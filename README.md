# calabria-monthly-fuels
produce monthly wildfire fuel maps using Annual_wildfire_susceptibility library, 20m res, 12 classes, RIRICO 2023 input. 

# env installation
strongly suggested environment preparation:

conda create --prefix .venv/ python=3.12.1 gdal

conda activate .venv/

pip install ipykernel

python -m pip install --no-cache-dir -U git+https://github.com/GiorgioMeschi/Annual_Wildfire_Susceptibility.git

python -m pip install --no-cache-dir -U git+https://github.com/GiorgioMeschi/geospatial_tools

