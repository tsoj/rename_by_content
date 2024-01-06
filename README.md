# rename_by_content
_Automatically rename files and reorganize them by looking at their contents._

rename_by_content is a Python script that can be used to automaticall guess
(hopefully) useful names and dates for files. It was written to
recover thousands of files that were deleted by mistake and partially
recovered by the excellent tool
[`photorec`](https://www.cgsecurity.org/wiki/PhotoRec).
This is a significantly customized fork. The original work is by sanette/San Vu Ngoc.

pdf, ai, doc, tar, zip, txt, mbox, ods, xls, xlsx, docx, docm, html,
rtf, odt, png, jpg, gif, bmp, tif, ppt, pptx, odp, odg

## Requirements

* A linux machine with several opensource utilities (should work on a
  mac too, in principle):

	- [exiftool](https://www.sno.phy.queensu.ca/~phil/exiftool/)
	  (extract files metadata). Please make sure that your exiftool
	  install is complete. For instance, find a `.docx` file and run
	  `exiftool myfile.docx`: then
	  check the result for the line:  
	  `File Type Extension : docx`
	- [libreoffice](https://www.libreoffice.org/) (to convert office documents to txt)
	- [pdftotext](https://www.xpdfreader.com/pdftotext-man.html) (usually included in any linux distro; otherwise install `poppler-utils`)
	- mutool (convert pdf to image. `sudo apt install mupdf-tools`. This one can be replaced by its many equivalents. But [mupdf](https://mupdf.com/) is great.)
	- [pandoc](https://pandoc.org/) (`sudo apt install pandoc`)

* Python 3

  With specific packages you might need to install:

  - pyexiftool (`python3 -m pip install -U pyexiftool`)
  - magic (`sudo apt install python3-magic`)
  - dateparser (`sudo apt install python3-dateparser` or `python3 -m pip install -U dateparser`)
  - unidecode (`sudo apt install python3-unidecode`)

## Installation

* download [rename_by_content.py](https://github.com/sanette/rename_by_content/blob/master/rename_by_content.py)

* make sure the other tools mentioned above are installed on your system

## Usage

### Command-line usage

```
python ./rename_by_content.py /path/to/dir [--rename_for_real]
```

Search for a title and a date for all files (recursively) under `/path/to/dir`, and find
a better name for the file. if `--rename_for_real` is specified, the file is also renamed
to this newly found file name.
