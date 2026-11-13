# Working without files

Every entry point accepts data already in memory, and the result can be
produced as bytes. Nothing has to touch the filesystem.

## Series from datasets

```{code-block} python
import pydicom
from rt_utils import RTStructBuilder

datasets = [pydicom.dcmread(path) for path in paths]

rtstruct = RTStructBuilder.create_new(dicom_series_path=datasets)
```

The list is sorted by slice position, using the same key as files read from
disk, so a path and a list of datasets are interchangeable.

:::{note}
Your list is not reordered in place. Sorting is applied to a copy, so the
list you passed keeps whatever order it had.
:::

## An existing structure set as a dataset

```{code-block} python
rtstruct = RTStructBuilder.create_from(
    dicom_series_path=datasets,
    rt_struct_path=pydicom.dcmread(rtstruct_bytes),
)
```

Both arguments take either form independently: a path for one and a dataset
for the other is fine.

## Saving to a buffer

{meth}`~rt_utils.rtstruct.RTStruct.save_to_memory` returns a rewound
`BytesIO`:

```{code-block} python
buffer = rtstruct.save_to_memory()

requests.post(url, files={"file": ("structures.dcm", buffer, "application/dicom")})
```

Because it is rewound, it can be handed straight to anything expecting a
readable file object:

```{code-block} python
import pydicom

ds = pydicom.dcmread(rtstruct.save_to_memory())
```

## A complete pipeline with no disk

```{code-block} python
:caption: Read from object storage, write back to it

import io
import pydicom
from rt_utils import RTStructBuilder

datasets = [
    pydicom.dcmread(io.BytesIO(bucket.get(key)))
    for key in bucket.list(prefix)
]

rtstruct = RTStructBuilder.create_new(dicom_series_path=datasets)
rtstruct.add_roi(mask=model(datasets), name="GTV")

bucket.put(f"{prefix}/structures.dcm", rtstruct.save_to_memory().read())
```

## Why this exists

DICOM arrives over the network as often as it arrives on disk: from a PACS,
a DICOMweb endpoint, an object store, a queue. Writing it to a temporary
directory first so a library can read it back is wasted work, and in a
container with a read-only filesystem it is not possible at all.
