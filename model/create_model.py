
#%%
import os
import rasterio as rio
from annual_wildfire_susceptibility.supranational_model import SupranationalModel

#%%

BASEP = '/home/sadc/share/project/calabria/data'
CONFIG = {     
    "batches" : 1, 
    "nb_codes_list" : [1],
    "list_features_to_remove" : ["lat", "lon", "veg_0"],
    "convert_to_month" : 1, # we turn on here here the month setting 
    "aggr_seasonal": 0, # we turn off the seasonal analysis.
    "wildfire_years" : [2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2015, 2017, 2018, 2019, 2020, 2021, 2022, 2023], 
    "nordic_countries" : {}, # nothing to exclude
    "save_dataset" : 0, # no intermediate df to save
    "reduce_fire_points" : 15, #sampling of fires
    "gridsearch" : 0,
    "ntree" : 100,
    "max_depth" : 15,
    "drop_neg_and_na_annual": 0, # we dont process negative values, they are present in the spi
    "name_col_y_fires" : "date_iso",
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


#%% train the model

# set working dir and initialize the class
dir_model_name = 'model'
working_dir = f'{BASEP}/{dir_model_name}/v4'
os.makedirs(working_dir, exist_ok=True)

supranationalmodel = SupranationalModel(working_dir, CONFIG)

# defines the input for dataset creation and model training
tiles_dir = '/home/sadc/share/project/calabria/data/ML' 
tiles = os.listdir(tiles_dir)
tiles = [tile for tile in tiles if os.path.isdir(os.path.join(tiles_dir, tile))]
# eclude tile_7 because it has no fires
tiles = [tile for tile in tiles if tile != 'tile_7']


# I use 4 dinamic variables (SPI)
monthly_variable_names = [  'spi_1m',
                            'spi_3m',
                            'spi_6m',
                            'spi_12m',
                            ]


years = list(range(2007, 2024)) # for training
months = list(range(1, 13)) # all months

# setting the structure of input dict
# in monthly analisys the folder structur is: country --> year_month (where month is 1, 2, ..., 12, ie 2020_1) --> list of tiff file of dynimac indices
monthly_files = {
    tile: {
        f'{year}_{month}': {
            tiffile: f'{BASEP}/ML/{tile}/climate_1m_shift/{year}_{month}/{tiffile}_bilinear_epsg3857.tif'
            for tiffile in monthly_variable_names
        }
        for year in years for month in months
    }
    for tile in tiles
}


# static variables
mandatory_input_dict = {tile:
                            [f"{BASEP}/ML/{tile}/dem/dem_20m_3857.tif",
                            f"{BASEP}/ML/{tile}/veg/veg_20m_3857.tif",
                            f"{BASEP}/ML/{tile}/fires/fires_2007_2023_epsg3857.shp"]
                            for tile in tiles}

# no other static input
optional_input_dict = None 


# create datasets
X_path, Y_path = supranationalmodel.creation_dataset_annual(annual_features_paths = monthly_files, 
                                                            mandatory_input_dict = mandatory_input_dict,
                                                            optional_input_dict = optional_input_dict
                                                        )

# create a model and save it
model_path = f'{working_dir}/RF_bilienarspi_100t_15d_15samples.sav'
supranationalmodel.creation_model(X_path, Y_path, model_path)



#%%
