"""Script to extract taxonomic and vernacular names from the GBIF taxonomy for BIOfid gazetteer."""

__author__ = "Martha Kandziora, edited by Manuel Schaaf"
__original_version__ = "0.20250306"
__version__ = "0.20250611"

import argparse
import gzip
from pathlib import Path
from typing import Final, Literal

import pandas as pd
from tqdm import tqdm

# def clean_scientific_name(row) -> str:
#     # If the 'scientificNameAuthorship' is present and not an empty string, modify the 'scientificName'
#     if (
#         pd.notna(row["scientificNameAuthorship"])
#         and row["scientificNameAuthorship"] != ""
#     ):
#         # Find the position of the 'scientificNameAuthorship' in 'scientificName'
#         auth_pos = row["scientificName"].rfind(row["scientificNameAuthorship"])

#         # Split the 'scientificName' into two parts: before and after the authorship
#         name_part = row["scientificName"][:auth_pos]
#         authorship_part = row["scientificName"][auth_pos:]

#         # Remove the 'scientificNameAuthorship' from the 'scientificName'
#         cleaned_name: str = name_part + authorship_part.replace(
#             row["scientificNameAuthorship"], "", 1
#         )

#         return cleaned_name.rstrip()
#     else:
#         # If no authorship to remove, return the original scientific name
#         return row["scientificName"]


BACKBONE_COLUMN_MAP: Final[dict[str, type]] = {
    "taxonID": int,
    "datasetID": str,
    "parentNameUsageID": str,
    "acceptedNameUsageID": str,
    "originalNameUsageID": str,
    "scientificName": str,
    "scientificNameAuthorship": str,
    "canonicalName": str,
    "genericName": str,
    "specificEpithet": str,
    "infraspecificEpithet": str,
    "taxonRank": str,
    "nameAccordingTo": str,
    "namePublishedIn": str,
    "taxonomicStatus": str,
    "nomenclaturalStatus": str,
    "taxonRemarks": str,
    "kingdom": str,
    "phylum": str,
    "class": str,
    "order": str,
    "family": str,
    "genus": str,
    "dwc:taxonID": str,
    "dwc:parentNameUsageID": str,
    "dwc:acceptedNameUsageID": str,
    "dwc:originalNameUsageID": str,
    "dwc:scientificNameID": str,
    "dwc:datasetID": str,
    "dwc:taxonomicStatus": str,
    "dwc:taxonRank": str,
    "dwc:scientificName": str,
    "dwc:scientificNameAuthorship": str,
    "col:notho": str,
    "dwc:genericName": str,
    "dwc:infragenericEpithet": str,
    "dwc:specificEpithet": str,
    "dwc:infraspecificEpithet": str,
    "dwc:cultivarEpithet": str,
    "dwc:nameAccordingTo": str,
    "dwc:namePublishedIn": str,
    "dwc:nomenclaturalCode": str,
    "dwc:nomenclaturalStatus": str,
    "dwc:kingdom": str,
    "dwc:phylum": str,
    "dwc:class": str,
    "dwc:order": str,
    "dwc:superfamily": str,
    "dwc:family": str,
    "dwc:subfamily": str,
    "dwc:tribe": str,
    "dwc:taxonRemarks": str,
    "dcterms:references": str,
}
GBIF_URI: Final[str] = "https://www.gbif.org/species/"
COL_URI: Final[str] = "https://www.catalogueoflife.org/data/taxon/"


def gbif_clean_scientific_name(row: pd.Series) -> str:
    scientificName: str = row["scientificName"].strip()
    if pd.notna(row["canonicalName"]) and row["canonicalName"].strip():
        return row["canonicalName"].strip()
    elif pd.notna(row["scientificNameAuthorship"]) and (
        scientificNameAuthorship := row["scientificNameAuthorship"].strip()
    ):
        return " ".join(
            scientificName.replace(scientificNameAuthorship, "", 1).strip().split()
        )
    elif (
        pd.notna(
            name_parts := row[
                ["genericName", "specificEpithet", "infraspecificEpithet"]
            ]
        ).any()
        and name_parts.str.strip().any()
    ):
        return " ".join(el for el in name_parts.str.strip().tolist() if el)
    else:
        return scientificName


def col_clean_scientific_name(row: pd.Series) -> str:
    scientificName: str = row["dwc:scientificName"].strip()
    if pd.notna(row["dwc:scientificNameAuthorship"]) and (
        scientificNameAuthorship := row["dwc:scientificNameAuthorship"].strip()
    ):
        return " ".join(
            scientificName.replace(scientificNameAuthorship, "", 1).strip().split()
        )
    elif (
        pd.notna(
            name_parts := row[
                [
                    "dwc:genericName",
                    "dwc:infragenericEpithet",
                    "dwc:specificEpithet",
                    "dwc:infraspecificEpithet",
                ]
            ]
        ).any()
        and name_parts.str.strip().any()
    ):
        return " ".join(str(el) for el in name_parts.str.strip().tolist() if el)
    else:
        return scientificName


def process_chunk(
    chunk: pd.DataFrame, dataset: Literal["gbif", "col"]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # remove taxa without canonical names - these are the odd letternumber combinations.

    # add URI
    match dataset:
        case "gbif":
            taxon_id_field = "taxonID"
            scientific_name_field = "scientificName"
            kingdom_field = "kingdom"

            uri = GBIF_URI.rstrip("/")

            clean_fn = gbif_clean_scientific_name

            # remove non-canonical names

            non_canonical_mask = chunk[kingdom_field].isin(
                {"Bacteria", "Viruses", "Archaea", "Chromista", "Protozoa"}
            )
            subset = chunk[non_canonical_mask].dropna(subset=["canonicalName"])

            if subset.empty:
                chunk = chunk[~non_canonical_mask]
            else:
                chunk = pd.concat([chunk[~non_canonical_mask], subset], axis=0)
        case "col":
            taxon_id_field = "dwc:taxonID"
            scientific_name_field = "dwc:scientificName"
            kingdom_field = "dwc:kingdom"

            uri = COL_URI.rstrip("/")

            clean_fn = col_clean_scientific_name
        case _:
            raise ValueError(f"Unknown dataset: {dataset}")

    chunk = chunk.dropna(subset=[scientific_name_field, taxon_id_field])

    chunk = chunk[
        ~chunk[scientific_name_field].str.contains("?", regex=False, na=False)
    ]

    #############################################################
    # do hand cleaning here: might be redundant now, as I filter for nonCanonical Names in most groups.
    chunk = chunk[
        ~chunk[scientific_name_field].str.contains(
            r"^SH\d*\.\d*FU$", regex=True, na=False
        )
    ]

    chunk = chunk[
        ~chunk[scientific_name_field].str.contains("BOLD:", regex=False, na=False)
    ]
    ##############################################
    chunk.loc[:, "Label"] = chunk.apply(clean_fn, axis=1)
    chunk.loc[:, "URI"] = chunk.loc[:, taxon_id_field].apply(lambda t: f"{uri}/{t}")

    # Split hybrids and non-hybrids
    hybrid_mask = chunk[scientific_name_field].str.contains("×", regex=False, na=False)

    df_taxa = chunk[~hybrid_mask][["Label", "URI"]]

    df_hybrids = chunk[hybrid_mask][["Label", "URI"]]
    df_hybrids.Label = df_hybrids.Label.str.replace(r"\s*×\s*", r" × ", regex=True)

    return df_taxa, df_hybrids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update GBIF backbone taxonomy for BIOfid search portal."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/backbone/current/"),
        help="Path to the root directory where the data will be stored.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/"),
        help="Path to the root directory where the data will be stored.",
    )

    dataset_group = parser.add_mutually_exclusive_group()
    dataset_group.add_argument(
        "--dataset",
        type=str,
        choices=["gbif", "col"],
        required=False,
    )
    parser.add_argument(
        "--col",
        action="store_const",
        const="col",
        dest="dataset",
    )
    parser.add_argument(
        "--gbif",
        action="store_const",
        const="gbif",
        dest="dataset",
    )

    parser.add_argument(
        "--chunk_size",
        type=int,
        default=100000,
        help="Path to the root directory where the data will be stored.",
    )
    parser.add_argument(
        "--taxonomic_names",
        action="store_true",
        help="Process GBIF Taxon data.",
    )
    parser.add_argument(
        "--vernacular_names",
        action="store_true",
        help="Process GBIF Vernacular Names data.",
    )

    args = parser.parse_args()

    if args.taxonomic_names:
        args.output.mkdir(parents=True, exist_ok=True)

        with (
            gzip.open(
                str(args.output / "taxonomic_names.csv.gz"), mode="wt", encoding="utf-8"
            ) as fp_taxa,
            gzip.open(
                str(args.output / "taxonomic_names_hybrids.csv.gz"),
                mode="wt",
                encoding="utf-8",
            ) as fp_hybrids,
            pd.read_csv(
                args.input / "Taxon.tsv",
                chunksize=args.chunk_size,
                index_col=False,
                sep="\t",
                on_bad_lines="warn",
                dtype=BACKBONE_COLUMN_MAP,
            ) as reader,
            tqdm(
                reader,
                desc="Processing GBIF Taxon.tsv",
                unit=" rows",
                unit_scale=True,
            ) as tqdm_chunks,
        ):
            _count_taxa, _count_hybrids = 0, 0
            for chunk in tqdm_chunks:
                _chunk_size = len(chunk)
                df_taxa, df_hybrids = process_chunk(chunk, args.dataset)

                df_taxa.to_csv(fp_taxa, index=False, header=False, sep=";", mode="a")
                _count_taxa += len(df_taxa)

                df_hybrids.to_csv(
                    fp_hybrids, index=False, header=False, sep=";", mode="a"
                )
                _count_hybrids += len(df_hybrids)

                tqdm_chunks.set_postfix(
                    {
                        "taxa": _count_taxa,
                        "hybrids": _count_hybrids,
                    }
                )
                tqdm_chunks.update(_chunk_size)

    if args.vernacular_names:
        vernacular_output = args.output / "vernacular_names"
        vernacular_output.mkdir(parents=True, exist_ok=True)

        vernacular_names = pd.read_csv(args.input / "VernacularName.tsv", sep="\t")

        match args.dataset:
            case "gbif":
                vernacular_names = vernacular_names[
                    ["taxonID", "vernacularName", "language"]
                ].rename(
                    columns={
                        "taxonID": "taxonID",
                        "vernacularName": "Label",
                        "language": "language",
                    }
                )
                uri = GBIF_URI.rstrip("/")
            case "col":
                vernacular_names = vernacular_names[
                    ["dwc:taxonID", "dcterms:language", "dwc:vernacularName"]
                ].rename(
                    columns={
                        "dwc:taxonID": "taxonID",
                        "dwc:vernacularName": "Label",
                        "dcterms:language": "language",
                    }
                )
                uri = COL_URI.rstrip("/")

        languages = vernacular_names.language.unique().tolist()
        for lang in tqdm(
            languages, desc="Processing GBIF VernacularName.tsv by Language"
        ):
            subset = vernacular_names[vernacular_names["language"] == lang]
            subset.loc[:, "URI"] = subset.loc[:, "taxonID"].apply(
                lambda t: f"{uri}/{t}"
            )
            subset[["Label", "URI"]].to_csv(
                vernacular_output / f"{lang}.csv.gz",
                index=False,
                header=False,
                sep=";",
                compression="gzip",
            )
