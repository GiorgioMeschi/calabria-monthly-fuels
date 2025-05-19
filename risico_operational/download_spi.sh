

current_year=$(date +%Y)
current_month=$(date +%m)

# Calculate previous month and year
if [ "$current_month" -eq 1 ]; then
    prev_month=12
    prev_year=$((current_year - 1))
else
    prev_month=$((10#$current_month - 1))  # 10# to force base 10
    prev_year=$current_year
fi

# Format months to two digits
current_month=$(printf "%02d" $current_month)
prev_month=$(printf "%02d" $prev_month)

for TS in 1 3 6 12; do
    # Download for current month
    aws s3 cp s3://edogdo/store/spi/chirps2/spi/spi${TS}/${current_year}/${current_month}/ \
        /home/sadc/share/project/calabria/data/raw/spi/${TS}/${current_year}/${current_month}/ \
        --recursive \
        --exclude "*" \
        --include "*CHIRPS2-SPI${TS}_${current_year}${current_month}*_tile4.tif"

    # Download for previous month
    aws s3 cp s3://edogdo/store/spi/chirps2/spi/spi${TS}/${prev_year}/${prev_month}/ \
        /home/sadc/share/project/calabria/data/raw/spi/${TS}/${prev_year}/${prev_month}/ \
        --recursive \
        --exclude "*" \
        --include "*CHIRPS2-SPI${TS}_${prev_year}${prev_month}*_tile4.tif"
done
