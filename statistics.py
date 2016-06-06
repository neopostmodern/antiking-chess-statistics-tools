import argparse
import csv
import glob
import os
import numpy
import matplotlib.pyplot as plot
import shutil


def to_number(string):
    try:
        return float(string)
    except ValueError:
        return None

field_names = []
OUTPUT_FOLDER = 'plots'

parser = argparse.ArgumentParser(description='Analyze (and visualize) logs')
parser.add_argument('directory', metavar='logs_directory', type=str, help='The folder containing the PlyMouth CSV logs')
parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')
parser.add_argument('-i', '--interactive', action='store_true', help='Show figures in window before saving')
parser.add_argument('-c', '--compact', action='store_true', help='Focus on significant part of figures (might exclude outliers)')
parser.add_argument('unnamed_fields', metavar='unnamed_field', type=str, nargs='+', help='Names of unnamed fields (iteration-level)')

args = parser.parse_args()

if not os.path.isdir(args.directory):
    print("Not a directory (or does not exist: %s" % args.directory)
    exit(1)

if os.path.isdir(OUTPUT_FOLDER):
    shutil.rmtree(OUTPUT_FOLDER)
os.mkdir(OUTPUT_FOLDER)

raw_data = []
game_lengths = []
row_lengths = []

print("Load data... ", end='')
for log_file_name in glob.glob(os.path.join(args.directory, '*.csv')):
    with open(log_file_name, newline='') as game_log_file:
        csv_reader = csv.reader(game_log_file, delimiter=';')

        header = True
        game_length = 0
        for row in csv_reader:
            if header:
                header = False
                if len(field_names) == 0:
                    field_names = row
                else:
                    assert field_names == row, "Logs of differing format supplied, aborting."
                continue

            raw_data.append(row)
            row_lengths.append(len(row))
            game_length += 1

        game_lengths.append(game_length)
print("OK.")

max_row_length = max(row_lengths)
maximum_game_length = max(game_lengths)
iteration_counts = numpy.bincount(row_lengths)[len(field_names)::len(args.unnamed_fields)][1:]
maximum_iterations = (max_row_length - len(field_names)) // len(args.unnamed_fields)
iteration_sizes = [sum(iteration_counts[iteration_index:]) for iteration_index in range(maximum_iterations)]

if args.verbose:
    print("Read %d games (%d plies)." % (len(game_lengths), len(raw_data)))
    print("> Game lengths:", game_lengths)
    print("> Maximum game length:", maximum_game_length)
    print("> Maximum row length: %d" % max_row_length)
    print("> Number of named fields: %d" % len(field_names), field_names)
    print("> Number of unnamed fields (per iteration): %d" % len(args.unnamed_fields), args.unnamed_fields)
    print("> Maximum iterations: %d" % maximum_iterations)
    print("> Iteration counts:", list(iteration_counts), iteration_sizes)

ply_data = numpy.ndarray((len(raw_data), len(field_names) + 1), dtype=numpy.float)

print("Processing data... ", end='')
iteration_data = [numpy.zeros((iteration_size, len(args.unnamed_fields)), dtype=numpy.float) for iteration_size in iteration_sizes]
running_iteration_indices = numpy.zeros(maximum_iterations)
for row_index, row in enumerate(raw_data):
    # copy all ply-level fields
    ply_data[row_index, :len(field_names)] = [to_number(value) for value in row[:len(field_names)]]
    # very good approximate of total used time is in the last field, add to ply-level data
    ply_data[row_index, len(field_names)] = row[len(row) - 1]

    # print(row, len(row))
    for iteration_index in range(maximum_iterations):
        base_index = len(field_names) + iteration_index * len(args.unnamed_fields)
        if len(row) > base_index:
            iteration_data[iteration_index][running_iteration_indices[iteration_index]] = [
                to_number(value) for value in row[base_index:base_index + len(args.unnamed_fields)]
            ]
            running_iteration_indices[iteration_index] += 1
print("OK.")

print("Create histograms for iterations... ", end='')
mean = numpy.mean(game_lengths)

plot.hist(game_lengths, bins=10, label="Game lengths")
plot.axvline(mean)
#
plot.savefig("%s/game_lengths.png" % OUTPUT_FOLDER)
if args.interactive:
    plot.show()
plot.close()
print("OK.")

print("Create plots for plies... ", end='')
ply_data = [ply_data[numpy.where(ply_data[:, 0] == ply_index + 1)] for ply_index in range(maximum_game_length)]
ply_indices = numpy.concatenate([ply_data[ply_index][:, 0] for ply_index in range(maximum_game_length)])
for field_name_index, field_name in enumerate(field_names):
    if field_name_index == 0: # ply index itself
        continue

    points = numpy.concatenate([ply_data[ply_index][:, field_name_index] for ply_index in range(maximum_game_length)])

    plot.title(field_name)
    plot.xlim([0, maximum_game_length + 1])  # one before and after
    plot.ylim([0, numpy.mean(points) + 3 * numpy.std(points)])
    plot.scatter(
        ply_indices,
        points,
        alpha=.2,
        c='r',
        edgecolors=''
    )
    mean = numpy.array([numpy.mean(ply_data[ply_index][:, field_name_index], axis=0) for ply_index in range(maximum_game_length)])
    std = numpy.array([numpy.std(ply_data[ply_index][:, field_name_index], axis=0) for ply_index in range(maximum_game_length)])

    plot.plot(range(1, maximum_game_length + 1), mean, color='b')
    plot.plot(range(1, maximum_game_length + 1), mean + std, color='g', alpha=.5)
    plot.plot(range(1, maximum_game_length + 1), mean - std, color='g', alpha=.5)
    plot.savefig("%s/%s.png" % (OUTPUT_FOLDER, field_name.replace(' ', '_').lower()))
    if args.interactive:
        plot.show()
    plot.close()
print("OK.")


print("Create combined graphs for unnamed fields per iterations... ", end='')
plot.title("Per iteration")
plot.ylim([0, 2000])
means = numpy.zeros([maximum_iterations, len(args.unnamed_fields)])
colors = ['b', 'g', 'r']
for iteration_index, iteration in enumerate(iteration_data):
    means[iteration_index] = numpy.ma.masked_invalid(iteration_data[iteration_index]).mean(0)

    for unnamed_field_index, unnamed_field in enumerate(args.unnamed_fields):
        plot.scatter(
            [iteration_index] * iteration.shape[0],  # a list of the same X value
            iteration[:, unnamed_field_index],  # actual data
            c=colors[unnamed_field_index],  # stable colors
            edgecolors='',
            alpha=.1
        )

for unnamed_field_index, unnamed_field in enumerate(args.unnamed_fields):
    plot.plot([mean[unnamed_field_index] for mean in means], label=unnamed_field, c=colors[unnamed_field_index])

plot.legend()
plot.savefig("plots/per-iteration.png")
if args.interactive:
    plot.show()
plot.close()
print("OK.")

print("Create histograms for iterations... ", end='')
for unnamed_field_index, unnamed_field in enumerate(args.unnamed_fields):
    plot.title(unnamed_field)
    bins = numpy.linspace(
        min([numpy.min(iteration_data[iteration_index][:, unnamed_field_index]) for iteration_index in range(maximum_iterations)]),
        max([numpy.max(iteration_data[iteration_index][:, unnamed_field_index]) for iteration_index in range(maximum_iterations)]),
        100
    )
    for iteration_index in range(maximum_iterations):
        # print(numpy.mean(iteration_data[iteration_index], axis=0))
        mean = numpy.mean(iteration_data[iteration_index], axis=0)[unnamed_field_index]

        plot.hist(iteration_data[iteration_index][:, unnamed_field_index], bins, label=("Iteration %d" % iteration_index))
        plot.axvline(mean)

    plot.savefig("plots/%s.png" % unnamed_field.replace(' ', '_').lower())
    if args.interactive:
        plot.show()
    plot.close()
print("OK.")

print("Goodbye.")



