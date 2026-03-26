source("tools_calc_access.R")

########## Set max time ##########

## maxtime is given in seconds
maxtime <- 60 * 60 # 60 minutes

########## Set grid expansion ##########

## if true this uses the expanded grid with higher resolution
use.expanded.grid <- T

#################### CREATE ACCESSIBILITY CSV FILES

# the make.access function takes some spatial data,
# and an incremental function,
# and produces .csv files with the value of accessibility at each location.
# the incremental function is where the accessibilty equation is defined
# (this could be a gravity measure, contour, etc, and for mobility it is just equal to 1)

nospatialdata <- data.frame() #create an empty dataframe for use in the mobility measure because it doesn't use other data

########## MOBILITY measure ##########

## Define the MOBILITY function and use it in make.access
incremental.mobility <- function(lat0, lon0, lat1, lon1, time, nospatialdata) {
    if (time < maxtime) {
        ## Check if location is within Nairobi
        founds <- findPolys(as.EventData(data.frame(EID=1, X=lon1, Y=lat1), projection=1), boundary)
        if (!is.null(founds) && nrow(founds) > 0)
            1 # use 1 to count number of points you can reach from current point (1232 are the total number of points in Nairobi so that we come up with sum(points)*1/#points, i.e. proportion of points you can reach)
        else
            0
    } else
        0 # 0 if outside this range (further than 30 mins away)
}

mobility.matatus <- make.access('matatus', nospatialdata, incremental.mobility)
write.csv(mobility.matatus, "mobility_matatus.csv", row.names=F)

mobility.walking <- make.access('walking', nospatialdata, incremental.mobility)
write.csv(mobility.walking, "mobility_walking.csv", row.names=F)

mobility.driving <- make.access('driving', nospatialdata, incremental.mobility)
write.csv(mobility.driving, "mobility_driving.csv", row.names=F)
