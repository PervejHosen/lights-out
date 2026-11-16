EXTENDED DATASET OF DAILY ELECTRICITY DEMAND, GENERATION,
LOAD SHEDDING, AND SUPPLY CONSTRAINTS IN BANGLADESH (2019–2026)


1. DATASET OVERVIEW

This dataset contains structured daily electricity-related information
for Bangladesh, including electricity demand, generation, load shedding,
supply-side constraints, generation-related information, weather-related
variables, and calendar variables.

The dataset extends the work published by Hossain, Md Ikrama; Nafs,
Tasnia; and Yeaser, Sakif (2025), “Structured Dataset of Daily
Electricity Demand, Generation, Load Shedding, and Supply Constraints
in Bangladesh (2019–2024),” Mendeley Data, V1, DOI:
10.17632/x7r7wdb39k.1.

The original dataset covers the period from November 21, 2019,
through December 30, 2024. Additional daily electricity reports were
collected from the Bangladesh Power Development Board (BPDB) to
extend the dataset through August 3, 2026.

The final dataset contains 2,428 daily records and 45 variables.


2. DATA SOURCE

The primary source of the newly collected data is the Bangladesh Power
Development Board (BPDB) and its publicly available Daily Generation
Archive:

https://misc.bpdb.gov.bd/daily-generation-archive

The original 2019–2024 portion of the dataset was obtained from the
previously published dataset by Hossain et al. (2025).

Additional records after December 30, 2024 were independently collected
from BPDB daily electricity reports.


3. DATA COLLECTION AND EXTRACTION

The BPDB daily reports were collected for the extended period after
December 30, 2024.

The extraction procedure used for the original dataset was applied to
the newly collected reports for variables whose format remained
compatible with the earlier reports.

However, the format and presentation of the BPDB reports changed
during the extended collection period. Changes included differences
in variable positions, labels, and textual presentation.

As a result, the original extraction procedure could not reliably
extract three variables from the newer report format. A separate
modified extraction procedure was therefore developed for these
three variables.

The affected variables were extracted independently, checked,
standardized, and aligned with their corresponding reporting dates.
The separately extracted variables were subsequently merged with
the main extracted dataset.

The final records were organized according to their corresponding
dates to produce the extended structured dataset.


4. HANDLING OF CHANGES IN BPDB REPORT FORMAT

Because the BPDB report format was not completely consistent
throughout the data-collection period, different extraction procedures
were required for selected variables.

The general approach was:

1. Apply the original extraction procedure to variables whose format
   remained compatible.

2. Identify variables affected by changes in the report format.

3. Develop a modified extraction procedure for the affected variables.

4. Extract the affected variables independently.

5. Standardize the extracted values.

6. Align the values using the corresponding reporting dates.

7. Merge the separately extracted variables with the main dataset.

8. Check the resulting records for date alignment, missing records,
   and consistency.

This approach allowed the original extraction procedure to be retained
where applicable while accommodating changes in the source-report
format.


5. UNAVAILABLE VARIABLE

The variable “Minimum Generation Forecast up to 8:00 hrs.”, which was
available in the earlier dataset, was not available in the BPDB reports
used for the extended period.

Because this information could not be consistently obtained from the
newer reports, no values were estimated, reconstructed, or artificially
generated for the missing period.

This preserves the distinction between information directly available
from the BPDB source reports and information that was unavailable
during the extended data-collection period.


6. DATA PROCESSING

The extracted information was organized into a structured tabular
format and integrated with the existing dataset.

Data processing included:

- Standardization of reporting dates
- Alignment of records by date
- Standardization of extracted variables
- Integration of separately extracted variables
- Checking for duplicate records
- Checking for missing records
- Checking the consistency of merged data
- Preservation of unavailable values where source information was
  not provided

Different date formats were encountered in the source reports,
including formats such as:

- DD.MM.YY
- DD-MM-YY
- DD-MMM-YYYY

These dates were standardized before the data were integrated into
the final dataset.


7. DATASET PERIOD

Original dataset:
November 21, 2019 – December 30, 2024

Extended records:
December 31, 2024 – August 3, 2026

Final dataset coverage:
November 21, 2019 – August 3, 2026


8. DATASET CONTENTS

The dataset contains variables related to electricity-system conditions,
including, where available:

- Electricity demand
- Electricity generation
- Load shedding
- Supply-side constraints
- Generation-related information
- Weather-related information
- Calendar and date-related characteristics
- Other variables included in the original dataset

Detailed variable names, descriptions, units, and data types are
provided in the accompanying Column_Descriptions.xlsx file.


9. INTENDED USE

The dataset is intended for research and educational purposes,
particularly:

- Electricity demand analysis
- Electricity generation analysis
- Load-shedding analysis
- Supply-constraint analysis
- Machine learning
- Load-shedding severity classification
- Explainable AI
- Energy-system research
- Power-system analytics


10. IMPORTANT NOTE

Because the source reports changed their formatting over time,
different extraction procedures were required for some variables.
The separately extracted variables were merged with the primary
dataset after date-based alignment and consistency checking.

Users intending to reproduce the extraction process should consider
the BPDB report format applicable to the specific period being studied.


11. DATA PROVENANCE AND ATTRIBUTION

This dataset extends the temporal coverage of the dataset published by:

Hossain, Md Ikrama; Nafs, Tasnia; Yeaser, Sakif (2025).
“Structured Dataset of Daily Electricity Demand, Generation,
Load Shedding, and Supply Constraints in Bangladesh (2019–2024).”
Mendeley Data, V1.
https://doi.org/10.17632/x7r7wdb39k.1

The records covering November 21, 2019, through December 30, 2024
are derived from and reused from the original dataset under the
Creative Commons Attribution 4.0 International (CC BY 4.0) licence.

The original dataset is licensed under the Creative Commons
Attribution 4.0 International (CC BY 4.0) licence:

https://creativecommons.org/licenses/by/4.0/

Additional records after December 30, 2024 were independently
collected from the Bangladesh Power Development Board (BPDB)
Daily Generation Archive:

https://misc.bpdb.gov.bd/daily-generation-archive

Changes were made by extending the dataset with these additional
records.

The original authors are not affiliated with, and have not endorsed,
this extended dataset.


12. CITATION

Users should cite this dataset using the citation generated by
Mendeley Data for this record.

When using or discussing the original 2019–2024 dataset, users
should also cite:

Hossain, Md Ikrama; Nafs, Tasnia; Yeaser, Sakif (2025).
“Structured Dataset of Daily Electricity Demand, Generation,
Load Shedding, and Supply Constraints in Bangladesh (2019–2024).”
Mendeley Data, V1.
https://doi.org/10.17632/x7r7wdb39k.1