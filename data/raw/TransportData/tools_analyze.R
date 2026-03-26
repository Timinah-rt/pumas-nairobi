source("tools_calc_access.R", chdir=T)

## Loop over all source points
## callback called for each source point as
##   callback(cell.lats, cell.lons, rr, cc, times)
source.iterate <- function(mode, callback) {
    prefix <- setup.access1(mode)

    ## Locations of all starting points
    cell.lats = seq(maxlat, minlat, by=-bigstep)
    if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
        cell.lats <- cell.lats[-length(cell.lats)]

    cell.lons = seq(minlon, maxlon, by=bigstep)

    indexes <- setup.access2(prefix, cell.lats, cell.lons)

    results <- data.frame(longitude=c(), latitude=c())

    ## Loop the all files
    for (rr in 1:min(length(cell.lats), nrow(indexes)))
        for (cc in 1:length(cell.lons)) {
            print(((rr - 1) * length(cell.lons) + cc) / (length(cell.lats) * length(cell.lons)))

            filename <- paste(prefix, '-', indexes[rr, cc], '.csv', sep='')
            times <- as.matrix(read.csv(filename, header=F))

            result <- callback(cell.lats, cell.lons, rr, cc, times)
            result$longitude <- cell.lons[cc]
            result$latitude <- cell.lats[rr]

            results <- rbind(results, result)
        }

    results
}

## Get the travel times from a given source point
get.times <- function(mode, lon, lat) {
    prefix <- setup.access1(mode)

    ## Locations of all starting points
    cell.lats <- seq(maxlat, minlat, by=-bigstep)
    if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
        cell.lats <- cell.lats[-length(cell.lats)]

    cell.lons <- seq(minlon, maxlon, by=bigstep)

    indexes <- setup.access2(prefix, cell.lats, cell.lons)

    rr <- which.min(abs(lat - cell.lats))
    cc <- which.min(abs(lon - cell.lons))
    print(c(rr, cc))

    filename <- paste(prefix, '-', indexes[rr, cc], '.csv', sep='')
    as.matrix(read.csv(filename, header=F))
}

## Calculate distances to the CBD
cbd.latitude <- -1.2921
cbd.longitude <- 36.8219

calc.cbd.distances <- function(lats, longs) {
    ## Use 1000 for maxspeed, so returned in km (note: if 1, would be in m)
    shortest.times(1000, cbd.latitude, cbd.longitude, lats, longs)
}

## Get the source file index for a given location
get.index <- function(mode, lat, lon) {
    prefix <- setup.access1(mode)

    ## Locations of all starting points
    cell.lats = seq(maxlat, minlat, by=-bigstep)
    if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
        cell.lats <- cell.lats[-length(cell.lats)]

    cell.lons = seq(minlon, maxlon, by=bigstep)

    indexes <- setup.access2(prefix, cell.lats, cell.lons)

    rr <- ceiling((lat - maxlat) / -bigstep)
    cc <- ceiling((lon - minlon) / bigstep)
    print(c(rr, cc))

    indexes[rr, cc]
}
