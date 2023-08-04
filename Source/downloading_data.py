import requests
from constants import simpathroot

sims = ["IllustrisTNG", "SIMBA"]
indexes = range(100)

"""Download the dataset from Flatiron Institute.
e.g. link: https://users.flatironinstitute.org/~camels/FOF_Subfind/IllustrisTNG/LH/LH_567/fof_subhalo_tab_005.hdf5 

Args:
    sims (lst): strings of simulations, "IllustrisTNG" or "SIMBA"
    indexes (ndarray): Indexes of subfind data from LH dataset to be downloaded.
"""

destination = simpathroot
url_prefix = "https://users.flatironinstitute.org/~camels/FOF_Subfind/"
suffix = "fof_subhalo_tab_033.hdf5"

for sim in sims:
    for i in indexes:
        url = url_prefix + sim + "/LH/LH_" + str(i) + "/" + suffix
        name = destination + sim + "_LH_" + str(i) + "_" + suffix
        r = requests.get(url)
        f = open(name, 'wb')
        f.write(r.content)
        print(f"File downloaded for {sim} set {i}")
        f.close
