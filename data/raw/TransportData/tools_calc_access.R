## Basic setup
source("tools_map.R")

require(plyr)


## Sets up global parameters for the mode of transit (walking, driving, matatus)
## Returns prefix
setup.access1 <- function(traveldata) {
  print("Initializing...")
  if (traveldata == "walking") {
      setup.walking()
    if (use.expanded.grid)
      prefix <- "nairobi-walking-extended/walking"
    else
      prefix <- "nairobi-walking/walking"
  } else if (traveldata == "driving") {
      setup.driving()
      if (use.expanded.grid)
          prefix <- "nairobi-driving-extended/driving"
      else
          prefix <- "nairobi-driving/driving"
  } else if (traveldata == "matatus")  {
      setup.matonwalk()
      if (use.expanded.grid)
          prefix <- "nairobi-matatus-extended/matonwalk"
      else
          prefix <- "nairobi-matatus/matonwalk"
  }

  return(prefix)
}

## Gets the indexes for each origin cell's transit times
setup.access2 <- function(prefix, cell.lats, cell.lons) {
  ## Read the index file
  indexes <- as.matrix(read.csv(paste(prefix, ".csv", sep=""), header=F))

  if (length(cell.lats) != dim(indexes)[1])
    print("ERROR: Index file rows does not match expected latitudes.")

  if (length(cell.lons) != dim(indexes)[2])
    print("ERROR: Index file columns does not match expected longitude.")

  return(indexes)
}

## Identify the grid boxes which contain each location
get.grid <- function(minlatcorner, minloncorner, size, xs, ys, gridcells=NA) {
  grid.x <- (xs - minloncorner) / size
  grid.y <- (ys - minlatcorner) / size
  if (!is.na(gridcells)) {
    grid.x[grid.x < 0 | grid.x >= cells] <- NA
    grid.y[grid.y < 0 | grid.y >= cells] <- NA
  }

  grid.x <- round(grid.x) + 1
  grid.y <- round(grid.y) + 1

  data.frame(rr=grid.y, cc=grid.x)
}

## Construct a dataset of access measures, with a row for each origin cell
##
## Parameters:
##
##   traveldata: the transit dataset: 'walking', 'driving', or 'matatus'
##   spatialdata: a data.frame with one row per spatial feature.  Must
##     contain columns X and Y; anything else can be used by
##     incremental
##   incremental: a function called for each destination
##
## incremental is called with the following arguments:
##   lat0, lon0: the starting location
##   lat1, lon1: the ending location
##   time: the time it takes to get from start to end locations, in seconds
##   data: a data.frame, containing rows of 'spatialdata' that are near
##     the ending location
##
## Returns:
##   A data.frame containing columns 'longitude', 'latitude' (for the
##   starting location) and 'access' (for the combined measure of
##   access across all destinations).
##
## Example:
## ## Load the spatial features
## spatialdata <- read.csv("../../Data/dataProcessed/CSUDLandUseRoadsBuildings/2010nairobi_LU/nairobi_LU_centroids.csv")
## ## Create the incremental function
## incremental <- function(lat0, lon0, lat1, lon1, time, data) {
##     nrow(data) * exp(-time / 600)
## }
## ## Calculate the access result
## results <- make.access('walking', landuse, incremental.contour)
make.access <- function(traveldata, spatialdata, incremental) {
    current.access.mode <<- traveldata

  prefix <- setup.access1(traveldata)

  ## Locations of all starting points
  cell.lats = seq(maxlat, minlat, by=-bigstep)
  if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
    cell.lats <- cell.lats[-length(cell.lats)]

  cell.lons = seq(minlon, maxlon, by=bigstep)

  indexes <- setup.access2(prefix, cell.lats, cell.lons)

  ## Create the access results
  print("Collecting results...")
  results <- data.frame(longitude=c(), latitude=c(), access=c())

  ## Loop the all files
  for (rr in 1:min(length(cell.lats), nrow(indexes)))
    for (cc in 1:length(cell.lons)) {
      print(((rr - 1) * length(cell.lons) + cc) / (length(cell.lats) * length(cell.lons)))

      grid <- get.grid(cell.lats[rr] - radius, cell.lons[cc] - radius, smallstep, spatialdata$X, spatialdata$Y, gridcells=cells)

      filename <- paste(prefix, '-', indexes[rr, cc], '.csv', sep='')
      times <- as.matrix(read.csv(filename, header=F))

      ## Locations of all endpoints
      ## Note that the direction of latitude is flipped here
      dest.lats <- seq(cell.lats[rr] - radius, cell.lats[rr] + radius, length.out=cells)
      dest.lons <- seq(cell.lons[cc] - radius, cell.lons[cc] + radius, length.out=cells)

      ## Aggregate access across all available approaches
      total <- 0
      for (rr1 in 1:dim(times)[1]) {
        for (cc1 in 1:dim(times)[2]) {
          mintime <- shortest.times(MAXSPEED, cell.lats[rr], cell.lons[cc], dest.lats[rr1], dest.lons[cc1]) * .9
          ## 0 is used to mean "unreachable" and mapquest can stop before if impassible
          if (!is.na(times[rr1, cc1]) && times[rr1, cc1] > 0 && times[rr1, cc1] > mintime)
            total <- total + incremental(cell.lats[rr], cell.lons[cc], dest.lats[rr1], dest.lons[cc1], times[rr1, cc1], subset(spatialdata, grid$cc == cc1 & grid$rr == rr1))
        }
      }

      results <- rbind(results, data.frame(longitude=cell.lons[cc], latitude=cell.lats[rr], access=total))
    }
  return(results)
#   ## Output to the access file
#   if (is.na(outfile)) {
#     print(paste("Outputing table to test-", traveldata, ".csv", sep=""))
#     write.csv(results, paste("../../Data/dataAccess/test-", traveldata, ".csv", sep=''), row.names=F)
#   } else if (outfile == F)
#     return(results)
#   else {
#     print(paste("Outputing table to", outfile))
#     write.csv(results, paste("../../Data/dataAccess/", outfile, ".csv", sep=''), row.names=F)
#     }
}


## Construct a dataset of spatial characteristics, by associating each centroid
## with an origin
##
## Parameters:
##
##   traveldata: the transit dataset: 'walking', 'driving', or 'matatus'
##   spatialdata: a data.frame with one row per spatial feature.  Must
##     contain columns X and Y; anything else can be used by
##     incremental.access.centroids.
##   integrate: a function called for each location
##
## integrate is called with the following arguments:
##    lat, lon: location of the grid cell in question
##    data: a data.frame containing rows of 'spatialdata' that are in
##      the grid cell
##
## Returns:
##   A data.frame containing columns 'longitude', 'latitude' (for the
##   measured location) and 'total' (for the measure of demographics
##   returned by integrate).
##
make.spatialdata.centroids <- function(traveldata, spatialdata, integrate, outfile=NA) {
  prefix <- setup.access1(traveldata)

  ## Locations of all starting points
  cell.lats = seq(maxlat, minlat, by=-bigstep)
  if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
    cell.lats <- cell.lats[-length(cell.lats)]

  cell.lons = seq(minlon, maxlon, by=bigstep)

  grid <- get.grid(minlat - bigstep / 2, minlon - bigstep / 2, bigstep, spatialdata$X, spatialdata$Y)

  results <- data.frame(longitude=c(), latitude=c(), total=c())

  ## Loop the all files
  for (rr in 1:length(cell.lats))
    for (cc in 1:length(cell.lons)) {
      print(((rr - 1) * length(cell.lons) + cc) / (length(cell.lats) * length(cell.lons)))

      total <- integrate(cell.lats[rr], cell.lons[cc], subset(spatialdata, grid$rr == rr & grid$cc == cc))

      results <- rbind(results, data.frame(longitude=cell.lons[cc], latitude=cell.lats[rr], total))
    }

  return(handle.output(results, outfile))
}

calc.time2closest <- function(traveldata, spatialdata, avgcount=1, outfile=NA) {
    prefix <- setup.access1(traveldata)

    ## Locations of all starting points
    cell.lats = seq(maxlat, minlat, by=-bigstep)
    if (cell.lats[length(cell.lats)] == minlat) # don't include endpoint if exact
        cell.lats <- cell.lats[-length(cell.lats)]

    cell.lons = seq(minlon, maxlon, by=bigstep)

    indexes <- setup.access2(prefix, cell.lats, cell.lons)

    results <- data.frame(longitude=c(), latitude=c(), time=c())

    ## Loop the all files
    for (rr in 1:length(cell.lats))
        for (cc in 1:length(cell.lons)) {
            print(((rr - 1) * length(cell.lons) + cc) / (length(cell.lats) * length(cell.lons)))

            grid <- get.grid(cell.lats[rr] - radius, cell.lons[cc] - radius, smallstep, spatialdata$X, spatialdata$Y, gridcells=cells)

            filename <- paste(prefix, '-', indexes[rr, cc], '.csv', sep='')
            times <- as.matrix(read.csv(filename, header=F))

            ## Locations of all endpoints
            ## Note that the direction of latitude is flipped here
            dest.lats <- seq(cell.lats[rr] - radius, cell.lats[rr] + radius, length.out=cells)
            dest.lons <- seq(cell.lons[cc] - radius, cell.lons[cc] + radius, length.out=cells)

            ## Collect times for each row
            loctimes <- c() # The time to each location
            for (ii in which(!is.na(grid$cc) & !is.na(grid$rr) & grid$cc < cells & grid$rr < cells)) {
                mintime <- shortest.times(MAXSPEED, cell.lats[rr], cell.lons[cc], dest.lats[grid$rr[ii]], dest.lons[grid$cc[ii]]) * .9
                mytime <- times[grid$rr[ii], grid$cc[ii]]
                ## 0 is used to mean "unreachable" and mapquest can stop before if impassible
                if (!is.na(mytime) && mytime > 0 && mytime > mintime)
                    loctimes <- c(loctimes, mytime)
            }

            if (length(loctimes) < avgcount)
                results <- rbind(results, data.frame(longitude=cell.lons[cc], latitude=cell.lats[rr], avgtime=NA))
            else if (avgcount == 1)
                results <- rbind(results, data.frame(longitude=cell.lons[cc], latitude=cell.lats[rr], avgtime=min(loctimes)))
            else
                results <- rbind(results, data.frame(longitude=cell.lons[cc], latitude=cell.lats[rr], avgtime=mean(sort(loctimes)[1:avgcount])))
        }

  return(handle.output(results, outfile))
}

## Calculate the great circle distance from one point to a list of
## others, providing a minimum distance.  Use the maximum speed to
## return a minimum amount of time to get there.
## maxspeed should be in m / s; return is seconds.
shortest.times <- function(maxspeed, lat0, long0, lats, longs) {
  deg2rad <- function(deg) return(deg*pi/180)

  lat0 <- deg2rad(lat0)
  long0 <- deg2rad(long0)
  lats <- deg2rad(lats)
  longs <- deg2rad(longs)

  R <- 6371 # Earth mean radius [km]
  d <- acos(sin(lat0)*sin(lats) + cos(lat0)*cos(lats) * cos(longs-long0)) * R

  (d * 1000) / maxspeed
}

handle.output <- function(results, outfile=NA) {
    ## Output to the access file
    if (is.na(outfile)) {
        print(paste("Outputing table to test-", ".csv", sep=""))
        write.csv(results, paste("../../Data/dataAccess/test-", ".csv", sep=''), row.names=F)
    } else if (outfile == F)
        return(results)
    else {
        print(paste("Outputing table to", outfile))
        write.csv(results, paste("../../Data/dataAccess/", outfile, ".csv", sep=''), row.names=F)
    }
}
