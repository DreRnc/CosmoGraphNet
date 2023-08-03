import requests 
import os

destination = os.getcwd() + '/Data/'
url_prefix = "https://users.flatironinstitute.org/~camels/FOF_Subfind/IllustrisTNG/LH/LH_"
name_prefix = destination + "FOF_Subfind_IllustrisTNG_LH_"
suffix = "fof_subhalo_tab_033.hdf5"

for i in range(10):
    url = url_prefix + str(i) + "/" + suffix
    name = name_prefix + str(i) + suffix
    r = requests.get(url)
    f = open(name, 'wb')
    f.write(r.content)
    print(f"File created for set {i}")
    f.close
