#----------------------------------------------------
# Graph Neural Network architecture
# Author: Pablo Villanueva Domingo
# Last update: 4/22
#----------------------------------------------------

import torch
import torch.nn.functional as F
from torch.nn import Sequential, Linear, ReLU, ModuleList
from torch_geometric.nn import MessagePassing, MetaLayer, LayerNorm
from torch_geometric.nn import global_mean_pool, global_max_pool, global_add_pool
from Source.constants import *

# Model for updating edge attritbutes
class EdgeModel(torch.nn.Module):
    def __init__(self, node_in, node_out, edge_in, edge_out, hid_channels, residuals=True, norm=False):
        super().__init__()

        self.residuals = residuals
        self.norm = norm

        layers = [Linear(node_in*2 + edge_in, hid_channels),
                  ReLU(),
                  Linear(hid_channels, edge_out)]
        if self.norm:  layers.append(LayerNorm(edge_out))

        self.edge_mlp = Sequential(*layers)


    def forward(self, src, dest, edge_attr, u, batch):
        # src, dest: [E, F_x], where E is the number of edges.
        # edge_attr: [E, F_e]
        # u: [B, F_u], where B is the number of graphs.
        # batch: [E] with max entry B - 1.

        out = torch.cat([src, dest, edge_attr], dim=1)
        #out = torch.cat([src, dest, edge_attr, u[batch]], 1)
        out = self.edge_mlp(out)
        if self.residuals:
            out = out + edge_attr
        return out

# Model for updating node attritbutes
class NodeModel(torch.nn.Module):
    def __init__(self, node_in, node_out, edge_in, edge_out, hid_channels, residuals=True, norm=False):
        super().__init__()

        self.residuals = residuals
        self.norm = norm

        layers = [Linear(node_in + 3*edge_out + 1, hid_channels),
                  ReLU(),
                  Linear(hid_channels, node_out)]
        if self.norm:  layers.append(LayerNorm(node_out))

        self.node_mlp = Sequential(*layers)

    def forward(self, x, edge_index, edge_attr, u, batch):
        # x: [N, F_x], where N is the number of nodes.
        # edge_index: [2, E] with max entry N - 1.
        # edge_attr: [E, F_e]
        # u: [B, F_u]
        # batch: [N] with max entry B - 1.

        row, col = edge_index
        out = edge_attr

        # Multipooling layer
        out1 = torch.zeros(x.size(0), out.size(1)).to(device)
        out2 = torch.zeros(x.size(0), out.size(1)).to(device)
        out3 = torch.zeros(x.size(0), out.size(1)).to(device)

        for i in range(x.size(0)):
            neighbour_edge_attr = out[row == i]
            out1[i] = torch.sum(neighbour_edge_attr, dim=0)
            out2[i] = torch.max(neighbour_edge_attr, dim=0)[0]
            out3[i] = torch.mean(neighbour_edge_attr, dim=0)
        
        # Concatenation for giving in input to MLP
        out = torch.cat([x, out1, out2, out3, u[batch]], dim=1)

        out = self.node_mlp(out)
        if self.residuals:
            out = out + x
        return out

# First edge model for updating edge attritbutes when no initial node features are provided
class EdgeModelIn(torch.nn.Module):
    def __init__(self, node_in, node_out, edge_in, edge_out, hid_channels, norm=False):
        super().__init__()

        self.norm = norm

        layers = [Linear(edge_in, hid_channels),
                  ReLU(),
                  Linear(hid_channels, edge_out)]
        if self.norm:  layers.append(LayerNorm(edge_out))

        self.edge_mlp = Sequential(*layers)


    def forward(self, src, dest, edge_attr, u, batch):

        out = self.edge_mlp(edge_attr)

        return out

# First node model for updating node attritbutes when no initial node features are provided
class NodeModelIn(torch.nn.Module):
    def __init__(self, node_in, node_out, edge_in, edge_out, hid_channels, norm=False):
        super().__init__()

        self.norm = norm

        layers = [Linear(3*edge_out + 1, hid_channels),
                  ReLU(),
                  Linear(hid_channels, node_out)]
        if self.norm:  layers.append(LayerNorm(node_out))

        self.node_mlp = Sequential(*layers)

    def forward(self, x, edge_index, edge_attr, u, batch):

        row, col = edge_index
        out = edge_attr

        # Multipooling layer
        out1 = torch.zeros(x.size(0), out.size(1)).to(device)
        out2 = torch.zeros(x.size(0), out.size(1)).to(device)
        out3 = torch.zeros(x.size(0), out.size(1)).to(device)

        for i in range(x.size(0)):
            neighbour_edge_attr = out[row == i]
            out1[i] = torch.sum(neighbour_edge_attr, dim=0)
            out2[i] = torch.max(neighbour_edge_attr, dim=0)[0]
            out3[i] = torch.mean(neighbour_edge_attr, dim=0)
        
        # Concatenation for giving in input to MLP
        out = torch.cat([out1, out2, out3, u[batch]], dim=1)

        out = self.node_mlp(out)

        return out

# Graph Neural Network architecture, based on the Graph Network (arXiv:1806.01261)
# Employing the MetaLayer implementation in Pytorch-Geometric
class GNN(torch.nn.Module):
    def __init__(self, node_features, n_layers, hidden_channels, linkradius, dim_out, only_positions, residuals=True):
        super().__init__()

        self.n_layers = n_layers
        self.link_r = linkradius
        self.dim_out = dim_out
        self.only_positions = only_positions

        # Number of input node features (0 if only_positions is used)
        node_in = node_features
        # Input edge features: |p_i-p_j|, p_i*p_j, p_i*(p_i-p_j)
        edge_in = 3
        node_out = hidden_channels
        edge_out = hidden_channels
        hid_channels = hidden_channels

        layers = []

        # Encoder graph block
        # If use only positions, node features are created from the aggregation of edge attritbutes of neighbors
        if self.only_positions:
            inlayer = MetaLayer(node_model=NodeModelIn(node_in, node_out, edge_in, edge_out, hid_channels),
                                edge_model=EdgeModelIn(node_in, node_out, edge_in, edge_out, hid_channels))

        else:
            inlayer = MetaLayer(node_model=NodeModel(node_in, node_out, edge_in, edge_out, hid_channels, residuals=False),
                                edge_model=EdgeModel(node_in, node_out, edge_in, edge_out, hid_channels, residuals=False))

        layers.append(inlayer)

        # Change input node and edge feature sizes
        node_in = node_out
        edge_in = edge_out

        # Hidden graph blocks
        for i in range(n_layers-1):

            lay = MetaLayer(node_model=NodeModel(node_in, node_out, edge_in, edge_out, hid_channels, residuals=residuals),
                            edge_model=EdgeModel(node_in, node_out, edge_in, edge_out, hid_channels, residuals=residuals))
            layers.append(lay)

        self.layers = ModuleList(layers)

        # Final aggregation layer
        self.outlayer = Sequential(Linear(3*node_out+1, hid_channels),
                              ReLU(),
                              Linear(hid_channels, hid_channels),
                              ReLU(),
                              Linear(hid_channels, hid_channels),
                              ReLU(),
                              Linear(hid_channels, self.dim_out))

    def forward(self, data):

        h, edge_index, edge_attr, u = data.x, data.edge_index, data.edge_attr, data.u

        # Message passing layers
        for layer in self.layers:
            h, edge_attr, _ = layer(h, edge_index, edge_attr, u, data.batch)

        # Multipooling layer
        addpool = global_add_pool(h, data.batch)
        meanpool = global_mean_pool(h, data.batch)
        maxpool = global_max_pool(h, data.batch)

        out = torch.cat([addpool,meanpool,maxpool,u], dim=1)

        # Final linear layer
        out = self.outlayer(out)

        return out
