This directory contains data files that describe travel times in
Nairobi, Kenya.  Three different modes of transportation are included:

 - Walking, according to MapQuest and filled in with Google Maps where
   MapQuest fails to find a route.

 - Driving, under normal traffic conditions.

 - Matatus, the informal public transportation network.

The travel times are computed from a gridded origin location to a
collection of gridded destination locations.  In the directories, each
file contains destination location times for a given origin location.
These are titled <mode>-###.csv.  The CSV is organized from north to
south, along rows, and west to east, along columns.  An additional
<mode>.csv file in each directory gives the organization of the
numbered files, again from north to south, along rows, and west to
east, along columns.

There are also "extended" versions of each grid, with larger
destination grids for each origin point, formed by "daisy-chaining"
together the original destination grids.

The directory also contains source files for working with the data:

 - calc_access.R shows how to calculate a simple mobility measure,
   using the functions in tools_calc_access.R

 - tools_analyze.R are a more general set of functions for performing
   arbitrary callback-based operations on the travel time data.

 - tools_calc_access.R contains underlying functions for setting up
   access to the grids and calculating access.

 - tools_map.R contains the grid origin and destination definitions
   and functions for plotting.

