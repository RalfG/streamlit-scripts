import io
import os
import re

import pandas as pd
import streamlit as st

from streamlit_utils import styled_download_button, encode_object_for_url


def dataframe_to_fasta_entry(
    csv_data,
    header_columns,
    sequence_columns,
    line_ending="\n",
    add_row_number=True,
    cleanup_header=True,
    max_header_length=None,
    max_line_length=58,
):
    for i, row in enumerate(csv_data.to_dict(orient='records')):
        row_number = str(i) + "|" if add_row_number else ""
        base_header = "|".join([row[h] for h in header_columns]).replace(" ", "_")
        if cleanup_header:
            base_header = re.sub("\W", "_", base_header)
        for t in sequence_columns:
            if isinstance(row[t], str):
                if row[t] not in ["ND", "TBC"]:
                    seq_column_title = t.replace(' ', '_')
                    tmp_base_header = base_header
                    if max_header_length:
                        max_base_header_length = max_header_length - len(row_number) - len(seq_column_title) - 1
                        if max_base_header_length < 5:
                            raise ValueError(
                                "`max_header_length` is too low to write meaningful fasta header."
                            )
                        if len(tmp_base_header) > max_base_header_length:
                            tmp_base_header = tmp_base_header[:max_base_header_length]
                    sequence_lines = line_ending.join(
                        [row[t][i:i+max_line_length] for i in range(0, len(row[t]), max_line_length)]
                    )
                    yield f">{row_number}{seq_column_title}|{tmp_base_header}{line_ending}{sequence_lines}{line_ending}"



def write_entries(csv_data, output_file):
    for line in dataframe_to_fasta_entry(csv_data):
        output_file.write(line)


def parse_output_name(filename):
    return os.path.splitext(os.path.basename(filename))[0] + ".fasta"


def main():
    st.set_page_config(
        page_title="CoV-AbDab converter",
        page_icon=":rocket:",
        layout="centered",
    )

    st.title("CoV-AbDab converter")
    st.header("About")
    st.markdown(
        """
        This script converts the CSV file from the
        [Coronavirus Antibody Database (CoV-AbDab)](http://opig.stats.ox.ac.uk/webapps/covabdab/)
        to a fasta sequence format.

        You can enter a URL to the CSV file, or upload another file below.

        _Disclaimer: This script was written independently from the authors and the team
        that developed the Coronavirus Antibody Database. If you use this database,
        please cite the original article:_

        >Matthew I. J. Raybould, Aleksandr Kovaltsuk, Claire Marks, Charlotte M. Deane (2020) CoV-AbDab: the Coronavirus Antibody Database. _Bioinformatics._ doi:[10.1093/bioinformatics/btaa739](doi.org/10.1093/bioinformatics/btaa739).

        More Streamlit scripts:
        [github.com/RalfG/streamlit-scripts](https://github.com/RalfG/streamlit-scripts)

        """
    )

    st.header("Convert CSV to fasta")
    st.subheader("Input")
    csv_url = st.text_input(
        "Enter the URL to the CoV-AbDab CSV file:",
        value="http://opig.stats.ox.ac.uk/webapps/covabdab/static/downloads/CoV-AbDab_230321.csv"
    )
    csv_uploaded = st.file_uploader(
        label="Or upload the CoV-AbDab CSV here:",
        type=[".csv", ".CSV"]
    )

    if csv_uploaded:
        csv_data = pd.read_csv(csv_uploaded)
        output_name = parse_output_name(csv_uploaded.name)
    else:
        csv_data = pd.read_csv(csv_url)
        output_name = parse_output_name(csv_url)

    header_columns = st.multiselect(
        label="Header columns",
        options=csv_data.columns.to_list(),
        default=[n for n in ["Name", "Ab or Nb", "Origin"] if n in csv_data.columns],
        help="Select columns to use in the fasta entry headers."
    )
    sequence_columns = st.multiselect(
        label="Sequence columns",
        options=csv_data.columns.to_list(),
        default=[n for n in ["CDRH3", "CDRL3", "VH or VHH", "VL"] if n in csv_data.columns],
        help=(
            "Select columns with peptide sequences. Each column will be written as as "
            "separate entry in the fasta file."
        )
    )
    max_header_length = st.number_input(
        label="Maximum header length (set to zero for unlimited length)",
        help="Setting multiple header columns can result in lengthy headers. This option truncates headers that are too long.",
        min_value=0,
        value=0
    )
    max_line_length = st.number_input(
        label="Maximum sequence line length",
        help="If the sequence is longer than this value, it will be wrapped over multiple lines.",
        min_value=10,
        value=58,
    )
    add_row_number = st.checkbox(
        label="Prefix CSV row number to fasta headers",
        help="Recommended to avoid duplicate headers and to be able to trace back sequences to their original source.",
        value=True
    )
    cleanup_header = st.checkbox(
        label="Replace non-word characters with underscores in headers",
        help="Some software does not accept special characters in fasta headers",
        value=True
    )

    if st.button("Convert to fasta"):
        status_placeholder = st.empty()
        status_placeholder.info(":hourglass_flowing_sand: Converting...")

        try:
            if max_header_length == 0:
                max_header_length = None
            entries = [l for l in dataframe_to_fasta_entry(
                csv_data, header_columns, sequence_columns,
                add_row_number=add_row_number,
                cleanup_header=cleanup_header,
                max_header_length=max_header_length,
                max_line_length=max_line_length
            )]
            entries_top = "".join(entries[:10])
            entries_b64 = encode_object_for_url("".join(entries))

        except Exception as e:
            status_placeholder.error(":x: Something went wrong.")
            st.exception(e)

        else:
            status_placeholder.success(":heavy_check_mark: Finished!")

            st.subheader("Original CSV")
            st.markdown("Only the first 500 entries are shown.")
            st.write(csv_data.head(500))

            st.subheader("Fasta entries")
            st.markdown("Only the first ten entries are shown.")
            st.code(entries_top, language=None)

            styled_download_button(
                f'data:file/fasta;base64,{entries_b64}',
                "Download fasta",
                download_filename=output_name
            )


if __name__ == "__main__":
    main()
