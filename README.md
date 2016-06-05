# antiking-chess-statistics-tools

    usage: statistics.py [-h] [-v] [-i] [-c]
                         logs_directory unnamed_field [unnamed_field ...]

    Analyze (and visualize) logs

    positional arguments:
      logs_directory     The folder containing the PlyMouth CSV logs
      unnamed_field      Names of unnamed fields (iteration-level)

    optional arguments:
      -h, --help         show this help message and exit
      -v, --verbose      Print verbose output
      -i, --interactive  Show figures in window before saving
      -c, --compact      Focus on significant part of figures (might exclude
                         outliers)

