import logging
from natsort import natsorted

from joblib import Parallel, delayed
import pandas as pd

try:
    from functools import lru_cache
except ImportError:
    from functools32 import lru_cache


def _merge_chip_and_input(chip_df, input_df):

    chip_df = chip_df.set_index("Chromosome Bin".split())
    input_df = input_df.set_index("Chromosome Bin".split())

    chip_df_nb_bins = len(chip_df)

    merged_df = chip_df.join(input_df,
                             how="left",
                             lsuffix=" ChIP",
                             rsuffix=" Input").reset_index()
    merged_df = merged_df[["Chromosome", "Bin", "Count ChIP", "Count Input"]]
    merged_df.columns = ["Chromosome", "Bin", "ChIP", "Input"]

    merged_df = merged_df.fillna(0)

    if not len(merged_df) == chip_df_nb_bins:
        assertion_message = [
            "Wrong number of rows after merging ChIP/Input.",
            "ChIP bins: " + str(chip_df_nb_bins),
            "Input bins: " + str(len(input_df)), "Head of ChIP df: ",
            chip_df.head().to_csv(sep=" "), "Head of Input df: ",
            input_df.head().to_csv(sep=" "), "Tail of ChIP df: ",
            chip_df.tail().to_csv(sep=" "), "Tail of Input df: ",
            input_df.tail().to_csv(sep=" "), "Number of bins in merged df: ",
            str(len(merged_df)), "Head of merged df: ",
            merged_df.head().to_csv(sep=" "), "Tail of merged df: ",
            merged_df.tail().to_csv(sep=" ")
        ]
        assertion_message = "\n".join(assertion_message)
        assert len(merged_df) == chip_df_nb_bins, assertion_message

    return merged_df


def merge_chip_and_input(chip_dfs, input_dfs, nb_cpu):

    # should be same length, since missing chromos get empty df
    # assert len(chip_dfs) == len(input_dfs)
    # if len(chip_dfs) != len(input_dfs):
    #     logging.info("Different number of chromosomes in ChIP and Input.")
    #     logging.info("Chromosomes in ChIP:" chip)

    logging.info("Merging ChIP and Input data.")
    merged_chromosome_dfs = Parallel(n_jobs=nb_cpu)(
        delayed(_merge_chip_and_input)(chip_df, input_df)
        for chip_df, input_df in zip(chip_dfs, input_dfs))
    return merged_chromosome_dfs


def get_total_number_of_reads(dfs):
    return sum([df.Count.sum() for df in dfs])


def ensure_same_chromosomes_in_list(sample1_dfs, sample2_dfs):

    d1 = create_chromsome_df_map(sample1_dfs)
    d2 = create_chromsome_df_map(sample2_dfs)

    d1, d2 = fill_missing_chromosomes(d1, d2)

    assert set(d1.keys()) == set(d2.keys())

    return d1, d2


def create_chromsome_df_map(dfs):

    sample_dict = {}
    for df in dfs:

        if df.empty:
            continue

        chromosome = df.head(1).Chromosome.values[0]
        sample_dict[chromosome] = df

    return sample_dict


def fill_missing_chromosomes(d1, d2):

    all_chromosomomes = set(d1.keys()).union(d2.keys())

    d1_missing = set(d2.keys()).difference(d1.keys())
    d2_missing = set(d1.keys()).difference(d2.keys())

    for chromosome in d1_missing:
        d1[chromosome] = pd.DataFrame(columns=["Chromosome", "Bin"])

    for chromosome in d2_missing:
        d2[chromosome] = pd.DataFrame(columns=["Chromosome", "Bin"])

    return d1, d2


def merge_same_files(sample1_dfs, sample2_dfs, nb_cpu):

    # if one list is missing a chromosome, we might pair up the wrong dataframes
    # therefore creating dicts beforehand to ensure they are paired up properly
    sample1_dfs, sample2_dfs = ensure_same_chromosomes_in_list(sample1_dfs,
                                                               sample2_dfs)

    assert len(sample1_dfs) == len(sample2_dfs)

    logging.info("Merging same class data.")
    merged_chromosome_dfs = Parallel(n_jobs=nb_cpu)(delayed(_merge_same_files)(
        sample1_dfs[chromosome],
        sample2_dfs[chromosome]) for chromosome in sample1_dfs.keys())

    return merged_chromosome_dfs


def _merge_same_files(sample1_df, sample2_df):

    merged_df = sample1_df.merge(sample2_df,
                                 how="outer",
                                 on=["Chromosome", "Bin"])
    # merged_df = merged_df[~merged_df.index.duplicated(keep='first')]

    return merged_df.fillna(0)
