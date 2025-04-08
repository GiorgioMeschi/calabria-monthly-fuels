current_year=$(date +%Y)
current_month=$(date +%m)

for TS in 1 3 6 12; do
    aws s3 cp s3://edogdo/store/spi/chirps2/spi/spi${TS}/${current_year}/${current_month}/ \
        /home/sadc/share/project/calabria/data/raw/spi/${TS}/${current_year}/${current_month}/ \
        --recursive \
        --exclude "*" \
        --include "*CHIRPS2-SPI${TS}_${current_year}${current_month}*_tile4.tif"
done

