import argparse
import csv
import glob
import os
import numpy
import matplotlib.pyplot as plot

field_names = []

parser = argparse.ArgumentParser(description='Analyze (and visualize) logs')
parser.add_argument('directory', metavar='logs_directory', type=str, help='The folder containing the PlyMouth CSV logs')
# parser.add_argument('--max_iterations', metavar='max_iterations', type=int, default=10, help='The maximum number of iterations in the logs')
parser.add_argument('unnamed_fields', metavar='unnamed_field', type=str, nargs='+', help='Names of unnamed fields (iteration-level)')

args = parser.parse_args()

if not os.path.isdir(args.directory):
    print("Not a directory (or does not exist: %s" % args.directory)
    exit(1)

raw_data = []
game_lengths = []
row_lengths = []

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

max_row_length = max(row_lengths)
maximum_game_length = max(game_lengths)
iteration_counts = numpy.bincount(row_lengths)[len(field_names)::len(args.unnamed_fields)][1:]
maximum_iterations = (max_row_length - len(field_names)) // len(args.unnamed_fields)
iteration_sizes = [sum(iteration_counts[iteration_index:]) for iteration_index in range(maximum_iterations)]

print("Read %d games (%d plies)." % (len(game_lengths), len(raw_data)))
print("> Game lengths:", game_lengths)
print("> Maximum game length:", maximum_game_length)
print("> Maximum row length: %d" % max_row_length)
print("> Number of named fields: %d" % len(field_names), field_names)
print("> Number of unnamed fields (per iteration): %d" % len(args.unnamed_fields), args.unnamed_fields)
print("> Maximum iterations: %d" % maximum_iterations)
print("> Iteration counts:", list(iteration_counts), iteration_sizes)

ply_data = numpy.ndarray((len(raw_data), len(field_names) + 1), dtype=numpy.int)
# print([(len(args.unnamed_fields), iteration_count) for iteration_count in iteration_counts])
# exit(1)

iteration_data = [numpy.zeros((iteration_size, len(args.unnamed_fields)), dtype=numpy.int) for iteration_size in iteration_sizes]
running_iteration_indices = numpy.zeros(maximum_iterations)
for row_index, row in enumerate(raw_data):
    # copy all ply-level fields
    ply_data[row_index, :len(field_names)] = row[:len(field_names)]
    # very good approximate of total used time is in the last field, add to ply-level data
    ply_data[row_index, len(field_names)] = row[len(row) - 1]

    # print(row, len(row))
    for iteration_index in range(maximum_iterations):
        base_index = len(field_names) + iteration_index * len(args.unnamed_fields)
        if len(row) > base_index:
            iteration_data[iteration_index][running_iteration_indices[iteration_index]] = [
                int(value) for value in row[base_index:base_index + len(args.unnamed_fields)]
            ]
            running_iteration_indices[iteration_index] += 1

for unnamed_field_index, unnamed_field in enumerate(args.unnamed_fields):
    plot.title(unnamed_field)
    bins = numpy.linspace(
        min([numpy.max(iteration_data[iteration_index][:, unnamed_field_index]) for iteration_index in range(maximum_iterations)]),
        max([numpy.max(iteration_data[iteration_index][:, unnamed_field_index]) for iteration_index in range(maximum_iterations)]),
        100
    )
    for iteration_index in range(maximum_iterations):
        # print(numpy.mean(iteration_data[iteration_index], axis=0))
        mean = numpy.mean(iteration_data[iteration_index], axis=0)[unnamed_field_index]

        plot.hist(iteration_data[iteration_index][:, unnamed_field_index], bins, label=("Iteration %d" % iteration_index))
        plot.axvline(mean)

    plot.savefig("plots/%s.png" % unnamed_field.replace(' ', '_').lower())
    plot.close()

ply_data = [ply_data[numpy.where(ply_data[:, 0] == ply_index + 1)] for ply_index in range(maximum_game_length)]
ply_indices = numpy.concatenate([ply_data[ply_index][:, 0] for ply_index in range(maximum_game_length)])
for field_name_index, field_name in enumerate(field_names):
    if field_name_index == 0: # ply index itself
        continue
    plot.title(field_name)
    plot.xlim([0, maximum_game_length + 1]) # one before and after
    plot.scatter(
        ply_indices,
        numpy.concatenate([ply_data[ply_index][:, field_name_index] for ply_index in range(maximum_game_length)]),
        alpha=.2,
        c='r',
        edgecolors=''
    )
    plot.plot(range(1, maximum_game_length + 1), [numpy.mean(ply_data[ply_index][:, field_name_index], axis=0) for ply_index in range(maximum_game_length)])
    # plot.show()
    plot.savefig("plots/%s.png" % field_name.replace(' ', '_').lower())
    plot.close()



