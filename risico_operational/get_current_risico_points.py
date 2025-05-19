
#%%
'''
implement logic of fuel map creation if new spi are available
[assume to have taken spi 1 3 6 and 12 month from s3 - 1h access token from terminal]
select the tile covering italy and clip + reproject over 22 calabria tiles
generate susceptibility per tile using the library
merge the suscpetibilities to calabria
generate the fuel map for calabria
generate 1 time only aspect and slope for risico txt
add to risico txt the fuel type 
'''

#%%

import os
import sys
import multiprocessing as mp
import geopandas as gpd
from datetime import datetime as dt
from datetime import timedelta
import logging

try: 
    from osgeo import gdal
except Exception as e:
    logging.info(e)
    logging.info('trying importing gdal direclty')
    import gdal

# chdir to filename repo directory to fix all the imports
f = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)
                            ))
                            
sys.path.append(f)
os.chdir(f)
print(f)

from risico_operational.settings import DATAPATH, TILEPATH, SPI_DATA
from model.run_model import compute_susceptibility
from risico_operational.pipeline_functions import (download_spi, clip_to_tiles, merge_susc_tiles,
                                                    generate_fuel_map, write_risico_files, reproject_raster_as)
                                
#%%

AGGREGATIONS = [1, 3, 6, 12] # month of aggregation for spi index
AOI_PATH = f'{DATAPATH}/aoi'
MERGED_SUSC_DIR = f'{DATAPATH}/susceptibility/v4' # path to save the merged susceptibility maps
VEG_CAL_DIR = f'{DATAPATH}/raw/vegetation' # path to the vegetation map
SUSC_THRESHOLD_DIR = f'{MERGED_SUSC_DIR}/thresholds' # path to the thresholds
TOPOGRAPHIC_DATA = f'{DATAPATH}/raw/dem' # path to the topographic data
OUTPUT_DIR = f'{DATAPATH}/risico' # path to save the output files



# functions for getting the available SPI files (4 files)
def get_spi1_rawfile(date): 
    aggr = 1
    year = date.strftime('%Y')
    month = date.strftime('%m')
    base_folderpath = f'{SPI_DATA}/{aggr}/{year}/{month}'
    try:
        day_of_interest = os.listdir(base_folderpath)[-1]
    except:
        day_of_interest = None
    return f'{base_folderpath}/{day_of_interest}/CHIRPS2-SPI{aggr}_{year}{month}{day_of_interest}_tile4.tif'

def get_spi3_rawfile(date): 
    aggr = 3
    year = date.strftime('%Y')
    month = date.strftime('%m')
    base_folderpath = f'{SPI_DATA}/{aggr}/{year}/{month}'
    # if isdir
    try:
        day_of_interest = os.listdir(base_folderpath)[-1]
    except:
        day_of_interest = None
    return f'{base_folderpath}/{day_of_interest}/CHIRPS2-SPI{aggr}_{year}{month}{day_of_interest}_tile4.tif'

def get_spi6_rawfile(date): 
    aggr = 6
    year = date.strftime('%Y')
    month = date.strftime('%m')
    base_folderpath = f'{SPI_DATA}/{aggr}/{year}/{month}'
    try:
        day_of_interest = os.listdir(base_folderpath)[-1]
    except:
        day_of_interest = None
    return f'{base_folderpath}/{day_of_interest}/CHIRPS2-SPI{aggr}_{year}{month}{day_of_interest}_tile4.tif'

def get_spi12_rawfile(date): 
    aggr = 12
    year = date.strftime('%Y')
    month = date.strftime('%m')
    base_folderpath = f'{SPI_DATA}/{aggr}/{year}/{month}'
    try:
        day_of_interest = os.listdir(base_folderpath)[-1]
    except:
        day_of_interest = None
    return f'{base_folderpath}/{day_of_interest}/CHIRPS2-SPI{aggr}_{year}{month}{day_of_interest}_tile4.tif'


def find_latest(path_fn, date):
    oldest_date = date - timedelta(days=90)
    current_date = date
    found = False
    while current_date > oldest_date:
        rawpath = path_fn(current_date)
        
        if os.path.isfile(rawpath):
            found = True
            break
        
        current_date = current_date - timedelta(days=15)
    if not found:
        raise ValueError('Could not find data')

    return rawpath, current_date



def pipeline(date):

    year = date.year
    month = date.month
    logging.info(f'Running for date: {date}')

    #tring dowloading the latest data
    print(os.getcwd()) 
    sh_file = './risico_operational/download_spi.sh'
    download_spi(sh_file)


    try:
        spi1_rawpath, found_date = find_latest(get_spi1_rawfile, date)
        spi1_actualmonth = found_date.strftime('%m')
        spi1_actualyear = found_date.strftime('%Y')
    except ValueError:
        raise Exception("Could not find data for spi1 in the latest 90 days")
    
    try:
        spi3_rawpath, found_date = find_latest(get_spi3_rawfile, date)
        spi3_actualmonth = found_date.strftime('%m')
        spi3_actualyear = found_date.strftime('%Y')
    except ValueError:        
        raise Exception("Could not find data for spi3 in the latest 90 days")
    
    try:
        spi6_rawpath, found_date = find_latest(get_spi6_rawfile, date)
        spi6_actualmonth = found_date.strftime('%m')
        spi6_actualyear = found_date.strftime('%Y')
    except ValueError:        
        raise Exception("Could not find data for spi6 in the latest 90 days")

    try:
        spi12_rawpath, found_date = find_latest(get_spi12_rawfile, date)
        spi12_actualmonth = found_date.strftime('%m')
        spi12_actualyear = found_date.strftime('%Y')
    except ValueError:        
        raise Exception("Could not find data for spi12 in the latest 90 days")

    logging.info(f'''
    found 
        SPI1: {spi1_rawpath}
        SPI3: {spi3_rawpath}
        SPI6: {spi6_rawpath}
        SPI12: {spi12_rawpath}
    ''')

    # if fuel map not already computed with found indeces do it
    out_monthly_fuel_folder = f'{OUTPUT_DIR}/monthly_fuel_maps'
    os.makedirs(out_monthly_fuel_folder, exist_ok=True)
    fuel_filename = (
        f'fuel12cl_{year}_{month}_'
        f'spi1-{spi1_actualmonth}_'
        f'spi3-{spi3_actualmonth}_'
        f'spi6-{spi6_actualmonth}_'
        f'spi12-{spi12_actualmonth}.tif'
    )
    fuel12cl_path = f'{out_monthly_fuel_folder}/{fuel_filename}'
    if not os.path.isfile(fuel12cl_path):

        tiles = os.listdir(TILEPATH)
        tile_df = gpd.read_file(f'{AOI_PATH}/grid_clean.geojsonl.json', driver='GeoJSONSeq')
        tile_df_wgs = tile_df.to_crs('EPSG:4326') #proj of the input SPI

        # get the current SPI data per calabria tile
        logging.info(f'preparing SPI per tile')
        valid_months = [spi1_actualmonth, spi3_actualmonth, spi6_actualmonth, spi12_actualmonth]
        valid_years = [spi1_actualyear, spi3_actualyear, spi6_actualyear, spi12_actualyear]
        pairs = [(_aggr, _year, _month) for _aggr, _year, _month in zip(AGGREGATIONS, valid_years, valid_months)]
        for _aggr, _year, _month in pairs:
            with mp.Pool(30) as p:
                p.starmap(clip_to_tiles, [(_aggr, _year, _month, tile, tile_df_wgs, year, month)
                                                                                for tile in tiles
                                                                                ])

            
        # get susceptibility map - includes already dynamic multiprocessing in the func
        logging.info(f'\nstart computiong susceptibility per tile\n')
        compute_susceptibility(years = [year], months = [month])

        # Merge susceptibility maps
        logging.info(f'\nget calabria susceptibility\n')
        merged_susc_file = merge_susc_tiles(tiles, year, month, MERGED_SUSC_DIR)

        # Generate fuel maps
        logging.info(f'\nget fuel map\n')
        veg_path = f'{VEG_CAL_DIR}/fuel_type.tif'
        mapping_path = f'{VEG_CAL_DIR}/veg_to_tf_fake.json'
        threashold_file = f'{SUSC_THRESHOLD_DIR}/thresholds.json'
        generate_fuel_map(merged_susc_file, threashold_file, veg_path, mapping_path, 
                           out_file = fuel12cl_path)

        #input/output for risico.txt
        dem_path = f'{TOPOGRAPHIC_DATA}/dem_calabria_20m_3857.tif'
        dem_wgs_path = f'{TOPOGRAPHIC_DATA}/dem_calabria_20m_wgs84.tif'
        slope_wgs_path = f'{TOPOGRAPHIC_DATA}/slope_calabria_20m_wgs84.tif'
        aspect_wgs_path = f'{TOPOGRAPHIC_DATA}/aspect_calabria_20m_wgs84.tif'
        if not os.path.exists(slope_wgs_path): # if slope and aspect already exist dont do it
            # use gdal to create slope and aspect
            logging.info(f'Calcualte slope')
            temp_slope_path = slope_wgs_path.replace('.tif', '0.tif')
            gdal.DEMProcessing(temp_slope_path, dem_path, 'slope')
            reproject_raster_as(temp_slope_path, slope_wgs_path, dem_wgs_path)
            os.remove(temp_slope_path)

            temp_aspect_path = aspect_wgs_path.replace('.tif', '0.tif')
            logging.info(f'Calcualte aspect')
            gdal.DEMProcessing(temp_aspect_path, dem_path, 'aspect')
            reproject_raster_as(temp_aspect_path, aspect_wgs_path, dem_wgs_path)
            os.remove(temp_aspect_path)


        # reproject fuel map to wgs84
        fuel12_wgs_path = f'{OUTPUT_DIR}/fuel12cl_wgs84.tif'
        if os.path.exists(fuel12_wgs_path):
            os.remove(fuel12_wgs_path)
        reproject_raster_as(fuel12cl_path, fuel12_wgs_path, dem_wgs_path)
        logging.info(f'Fuel12cl reprojected to {fuel12_wgs_path}')

        # create a txt file in which each row has x and y coordinates and the value of the hazard
        risico_outfile = f'{OUTPUT_DIR}/risico_calabria.txt'
        logging.info(f'Write risico file to {risico_outfile}')
        if os.path.exists(risico_outfile):
            os.remove(risico_outfile)

        write_risico_files(fuel12_wgs_path, slope_wgs_path, aspect_wgs_path, risico_outfile)
        logging.info(f'{risico_outfile} created!!!')        


if __name__ == '__main__':

    # get the current date
    date = dt.now()

    log_filename = f'{OUTPUT_DIR}/logs/pipeline_{date.strftime('%Y-%m-%d')}.log'
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    logging.basicConfig(level=logging.INFO,
                        format = '[%(asctime)s] %(filename)s: {%(lineno)d} %(levelname)s - %(message)s',
                        datefmt ='%H:%M:%S',
                        filename = log_filename)
    
    pipeline(date)

