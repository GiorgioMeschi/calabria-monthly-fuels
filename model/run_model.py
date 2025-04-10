

#%%

from annual_wildfire_susceptibility.susceptibility import Susceptibility
from risico_operational.settings import TILEPATH, DATAPATH

import os
import multiprocessing
import psutil
import time
import logging
from functools import wraps
import shutil


#%% inputs

BASEP = DATAPATH  # '/home/sadc/share/project/calabria/data'
VS = 'v4'
CONFIG = {     
    "batches" : 1, 
    "nb_codes_list" : [1],
    "list_features_to_remove" : ["veg_0"],
    "convert_to_month" : 1, # we turn on here here the month setting 
    "aggr_seasonal": 0, # put 1 if seasonal analysis, same as month but 1 is summer and 2 is winter, the aggr in fires will change accordingly.
    "wildfire_years" : [],
    "nordic_countries" : {}, 
    "save_dataset" : 0,
    "reduce_fire_points" : 10,
    "gridsearch" : 0,
    "ntree" : 750,
    "max_depth" : 15,
    "drop_neg_and_na_annual": 0, # we dont process no data
    "name_col_y_fires" : "date",
    "make_CV" : 0,
    "make_plots" : 0, 
    # settings for validation - skipped    
    "validation_ba_dict" :   {
                                "fires10" : "",
                                "fires90" : ""
                                    },
    "country_name" : "", 
    "pixel_size" : 100, 
    "user_email" : "",
    "email_pwd" : "" 
}  

WORKING_DIR = f'{TILEPATH}/susceptibility/{VS}'
MODEL_PATH = f'{BASEP}/model/{VS}/RF_bilienarspi_100t_15d_15samples.sav'
X_PATH = f"{BASEP}/model/{VS}/X_no_coords_clip.csv"

# vs = ['v4']
# for VS in vs:
#     WORKING_DIR = f'{BASEP}/ML/susceptibility/{VS}'
#     X_PATH = f"{BASEP}/model/{VS}/X_no_coords.csv"
#     #open save 3 lines and save it as clip
#     df = pd.read_csv(X_PATH, index_col=0)
#     df = df.iloc[0:3,:]
#     df.to_csv(f"{BASEP}/model/{VS}/X_no_coords_clip.csv")


def memory_watch_psutil_v2(func, interval=1):
    import threading
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the process information for memory tracking
        process = psutil.Process()

        # Record memory usage before function call
        mem_before = process.memory_info().rss / (1024 * 1024)  # Convert to MB
        mem_peak = mem_before

        # Record the starting time
        start_time = time.time()

        # Function to monitor memory usage periodically
        def monitor_memory():
            nonlocal mem_peak
            while monitoring:
                mem_current = process.memory_info().rss / (1024 * 1024)  # Convert to MB
                mem_peak = max(mem_peak, mem_current)  # Update peak memory if current usage is higher
                time.sleep(interval)  # Wait for the next interval to check memory again

        # Start monitoring in a separate thread
        monitoring = True
        monitor_thread = threading.Thread(target=monitor_memory)
        monitor_thread.start()

        # Execute the main function
        try:
            result = func(*args, **kwargs)
        finally:
            # Stop memory monitoring after function execution
            monitoring = False
            monitor_thread.join()

        # Record memory usage after function call
        mem_after = process.memory_info().rss / (1024 * 1024)  # Convert to MB
        end_time = time.time()

        logging.info(f"Peak memory usage during '{func.__name__}': {mem_peak - mem_before:.2f} MB")
        logging.info(f"Memory usage change after '{func.__name__}': {mem_after - mem_before:.2f} MB")
        logging.info(f"Execution time for '{func.__name__}': {(end_time - start_time)/60:.2f} minutes")

        return result
    return wrapper



#%% run in parallel

@memory_watch_psutil_v2
def compute_month_susceptibility(tile, year, month):

    monthly_variable_names = [  'spi_1m',
                                'spi_3m',
                                'spi_6m',
                                'spi_12m',
                                ]
    climate_foldername = 'climate' # climate_1m_shift
    monthly_files = {f'{year}_{month}': {tiffile : f'{TILEPATH}/{tile}/{climate_foldername}/{year}_{month}/{tiffile}_bilinear_epsg3857.tif'
                        for tiffile in monthly_variable_names}
                            }                         

    dem_path = f"{TILEPATH}/{tile}/dem/dem_20m_3857.tif"
    veg_path = f"{TILEPATH}/{tile}/veg/veg_20m_3857.tif"
    optional_input_dict = {}

    working_directory = f'{BASEP}/ML/{tile}/susceptibility/{VS}/{year}_{month}'
    # output_like = f'{working_directory}/susceptibility/annual_maps/Annual_susc_{year}_{month}.tif'
    # if not os.path.exists(output_like):

    os.makedirs(working_directory, exist_ok=True)
    susceptibility = Susceptibility(dem_path, veg_path, # mandatory vars
                                    working_dir = working_directory,
                                    optional_input_dict = optional_input_dict, # optional layers
                                    config = CONFIG # configuration file
                                    ) 

    susceptibility.run_existed_model_annual(MODEL_PATH, 
                                            annual_features_paths = monthly_files,
                                            training_df_path = X_PATH,
                                            start_year = f'{year}_{month}')

    logging.info(f"Finished computing susceptibility for {tile} in {year}_{month}\n")
    time.sleep(1)
    



# adaptive multiprocessing
def monitor_memory():
    """Returns available memory percentage."""
    return psutil.virtual_memory().available / psutil.virtual_memory().total * 100


def dynamic_worker(task_queue, min_workers=4, max_workers=40, check_interval=5):
    """
    Dynamically adjusts how many new tasks are launched based on available memory.
    Every 'check_interval' seconds it checks memory and adjusts the allowed number of
    concurrent worker processes. Running processes are allowed to complete.
    """
    allowed_workers = 5  # starting allowed concurrent workers
    running_processes = []

    while not task_queue.empty() or running_processes:
        # Check memory and adjust allowed_workers
        available_mem = monitor_memory()
        print(f"Available memory: {available_mem:.2f}%")
        if available_mem < 15:
            allowed_workers = max(min_workers, allowed_workers - 4) #3
        elif available_mem > 30:
            allowed_workers = min(max_workers, allowed_workers + 2)
        print(f"Allowed workers: {allowed_workers}")

        # Remove any processes that have finished
        running_processes = [p for p in running_processes if p.is_alive()]

        # Launch new tasks if we haven't reached the current allowed limit
        while not task_queue.empty() and len(running_processes) < allowed_workers:
            year, month, tile = task_queue.get()
            p = multiprocessing.Process(target=compute_month_susceptibility, args=(tile, year, month))
            p.start()
            running_processes.append(p)

        # Wait for the check interval before re-assessing memory
        time.sleep(check_interval)

    # Wait for any remaining processes to finish
    for p in running_processes:
        p.join()


# main function 
def compute_susceptibility(years, months):
    # set logging
    # log_filename = f'/home/sadc/share/project/calabria/data/susceptibility/{VS}/susc.log'
    # os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    # logging.basicConfig(level=logging.INFO,
    #                     format = '[%(asctime)s] %(filename)s: {%(lineno)d} %(levelname)s - %(message)s',
    #                     datefmt ='%H:%M:%S',
    #                     filename = log_filename)

    # turn off all the worning of rasterio and gdal
    logging.getLogger('rasterio').setLevel(logging.ERROR)
    logging.getLogger('osgeo').setLevel(logging.ERROR)

    # years = [YEAR] #list(range(2007, 2019)) 
    # months = [MONTH] #list(range(1, 13))  
    tiles_dir = TILEPATH
    tiles = os.listdir(tiles_dir)
    tiles = [tile for tile in tiles if os.path.isdir(os.path.join(tiles_dir, tile))]

    task_queue = multiprocessing.Queue()
    for year in years:
        for month in months:
            for tile in tiles:
                task_queue.put((year, month, tile))

    dynamic_worker(task_queue,
                   check_interval = 8)


# if __name__ == "__main__":
#     compute_susceptibility()



#%%

