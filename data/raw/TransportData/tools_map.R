library(PBSmapping)

use.expanded.grid <- F

setup.driving <- function() {
    if (use.expanded.grid) {
        minlon <<- 36.65
        maxlon <<- 37.176427
        minlat <<- -1.45
        maxlat <<- -1.15

        radius <<- .4
        cells <<- 100
    } else {
        minlon <<- 36.65
        maxlon <<- 37.176427
        minlat <<- -1.45
        maxlat <<- -1.15

        bigstep <<- .01 # Space between points i

        radius <<- .16
        cells <<- 10
    }

    bigstep <<- .01 # Space between points i

    smallstep <<- 2*radius / cells # Space between points j
    MAXSPEED <<- 30 # 30 m/s = 67 mi/hr
}

setup.walking <- function() {
    minlon <<- 36.65
    maxlon <<- 37.176427
    minlat <<- -1.45
    maxlat <<- -1.15

    bigstep <<- .01

    if (use.expanded.grid) {
        radius <<- .16
        cells <<- 40
    } else {
        radius <<- .04
        cells <<- 10
    }

    smallstep <<- 2*radius / cells

    MAXSPEED <<- 2 # 2 m/s = 4.5 mi/hr
}

setup.matonwalk <- function() {
  minlon <<- 36.65
  maxlon <<- 37.176427
  minlat <<- -1.45
  maxlat <<- -1.15

  bigstep <<- .01

  if (use.expanded.grid) {
      radius <<- .16
      cells <<- 40
  } else {
      radius <<- .04
      cells <<- 10
  }

  smallstep <<- 2*radius / cells

  MAXSPEED <<- 20 # 20 m/s = 45 mi/hr
}

get.scores <- function(csvpath, myminlon, mylonstep, mymaxlat, mylatstep) {
  data <- read.csv(csvpath, header=F)
  if (sum(data != 0) == 0) {
    print("No non-zero values.")
    return(0)
  }

  events <- data.frame(X=c(), Y=c(), Z=c())
  for (ii in 1:nrow(data))
    for (jj in 1:ncol(data)) {
      events <- rbind(events, data.frame(X=c(myminlon + mylonstep * (jj-1)), Y=c(mymaxlat - mylatstep * (ii-1)), Z=c(data[ii, jj])))
    }

  return(events)
}

map.bubbles <- function(csvpath, basedir) {
  events <- get.scores(csvpath, minlon, bigstep, maxlat, bigstep)

  map.roads(basedir, ylim=c(-1.5, -1), xlim=c(36.6, 37.13))

  events$EID <- 1:nrow(events)

  events <- as.EventData(events)

  addBubbles(events, type="volume", max.size=.1, symbol.zero="", symbol.bg=rgb(1,0,0,0.7))
}

map.bubbles.part <- function(csvpath, basedir, myminlon, mylonstep, mymaxlat, mylatstep) {
    data <- read.csv(csvpath, header=F)
    if (sum(data != 0) == 0) {
        print("No non-zero values.")
        return(0)
    }

    map.roads(basedir)

    events <- data.frame(X=c(), Y=c(), Z=c())
    for (ii in 1:nrow(data))
        for (jj in 1:ncol(data)) {
            events <- rbind(events, data.frame(X=c(myminlon + mylonstep * (jj-1)), Y=c(mymaxlat - mylatstep * (ii-1)), Z=c(data[ii, jj])))
        }
    events$EID <- 1:nrow(events)

    events <- as.EventData(events)

    addBubbles(events, type="perceptual", max.size=.1, symbol.bg=rgb(1,0,0,0.7))
}

get.center <- function(index, dlon, dlat) {
    ## Count up just the way I do
    lat <- maxlat
    while (lat > minlat) {
        lon <- minlon
        while (lon < maxlon) {
            index <- index - 1
            if (index == 0)
                break

            lon <- lon + dlon
        }
        if (index == 0)
            break

        lat <- lat - dlat
    }

    return(c(lat, lon))
}

get.scores.centered <- function(csvpath, index) {
  center <- get.center(index, .01, .01)

  return(get.scores(csvpath, center[2] - radius, smallstep, center[1] + radius, smallstep))
}

map.bubbles.stata <- function(csvpath) {
    events <- read.csv(csvpath)
    names(events) <- c("X", "Y", "Z")

    map.roads(basedir, ylim=c(-1.5, -1), xlim=c(36.6, 37.13))

    events$EID <- 1:nrow(events)
    events <- as.EventData(events)
    addBubbles(events, type="volume", max.size=.1, symbol.zero="", symbol.bg=rgb(1,0,0,0.7))
}

total.points.reachable <- function() {
    jacross <- floor((maxlon + radius - (minlon - radius)) / smallstep)
    jdown <- floor((maxlat + radius - (minlat - radius)) / smallstep)
    jacross * jdown
}

total.locations.reachable <- function(x, y) {
    sum(x <= maxlon + radius & x >= minlon - radius & y <= maxlat + radius & y >= minlat - radius)
}
