
import os
import json
import numpy as np
from geospatial_tools import FF_tools as ff
from geospatial_tools import geotools as gt

fft = ff.FireTools()
Raster = gt.Raster()

vs = 'v4'
folder_susc = f'/home/sadc/share/project/calabria/data/susceptibility/{vs}'
susc_names = [i for i in os.listdir(folder_susc) if i.endswith('.tif')]
threashold_file = f'/home/sadc/share/project/calabria/data/susceptibility/{vs}/thresholds/thresholds.json'
thresholds = json.load(open(threashold_file))
tr1, tr2 = thresholds['lv1'], thresholds['lv2']
veg_path = '/home/sadc/share/project/calabria/data/raw/vegetation/vegetation_ml.tif'
mapping_path = '/home/sadc/share/project/calabria/data/raw/vegetation/veg_to_tf.json'
out_folder = f'/home/sadc/share/project/calabria/data/fuel_maps/{vs}'
os.makedirs(out_folder, exist_ok=True)
susc_class_oufolder = f'/home/sadc/share/project/calabria/data/susceptibility/{vs}/susc_classified'
ft_outfolder = f'/home/sadc/share/project/calabria/data/fuel_type_4cl/{vs}'
os.makedirs(susc_class_oufolder, exist_ok=True)
os.makedirs(ft_outfolder, exist_ok=True)

# get hazards
for idx, susc_filename in enumerate(susc_names):
    print(idx)
    susc_file = f"{folder_susc}/{susc_filename}"
    hazard_filename = susc_filename.replace('susc', 'fuel')

    inputs = dict(
        susc_path = susc_file,
        thresholds= [tr1, tr2],
        veg_path = veg_path,
        mapping_path = mapping_path,
        out_hazard_file = f"{out_folder}/{hazard_filename}"
        )

    _, susc_class, ft_arr = fft.hazard_12cl_assesment(**inputs)
    # save
    Raster.save_raster_as(susc_class, 
                          f'{susc_class_oufolder}/{susc_filename}',
                          susc_file, dtype = np.int8(), nodata =0)
    
    Raster.save_raster_as(susc_class, 
                          f'{susc_class_oufolder}/{susc_filename}',
                          susc_file, dtype = np.int8(), nodata =0)
    if idx == 0:
        ft_filename = 'ft.tif'
        Raster.save_raster_as(ft_arr,
                                f'{ft_outfolder}/{ft_filename}',
                                susc_file, dtype = np.int8(), nodata =0)
    




