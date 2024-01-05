# TODO
# pdf
# doc
# tar
# zip
# txt-ascii
# txt-utf-8
# mbox
# ods,
# xls', 'xlsx


from pathlib import Path
import subprocess
import tempfile
import os
import zipfile
import codecs
import shutil
import re
import exiftool
import atexit
import sys
import datetime
from unidecode import unidecode

from inspect import currentframe, getframeinfo

MIN_YEAR = 1900
DEBUG_ENABLED = False

tempdirHandle = tempfile.TemporaryDirectory()
tempdir = tempdirHandle.name

et = exiftool.ExifToolHelper()


def globalCleanup():
    tempdirHandle.cleanup()
    et.terminate()


atexit.register(globalCleanup)


def print_error(msg=None):
    cf = currentframe()
    filename = getframeinfo(cf).filename
    print(f"findTitles: Error at {filename}:{cf.f_back.f_lineno}")
    if msg:
        print(msg)


def print_debug(*args):
    cf = currentframe()
    filename = getframeinfo(cf).filename
    if DEBUG_ENABLED:
        print(f"Info at {filename}:{cf.f_back.f_lineno}:", *args)


def get_valid_filename(s, convert_accent=True, max_len=128):
    """Return a clean filename"""

    s = s.strip().replace(" ", "_")
    s = s.strip().replace("\000", "")
    if convert_accent:
        s = unidecode(s)  # "ça c'est sûr" ==> "ca c'est sur"
    s = re.sub(r"[^A-Za-z0-9_-]", "_", s)
    s = s[:max_len]
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def to_utf8(string, encoding="utf-8"):
    """Convert from given encoding to 'unicode' type

    There might be some losses. We never know what we are given,
    especially when reading files.
    """
    if isinstance(string, str):
        return string
    else:
        try:
            s = string.decode(encoding)
        except UnicodeDecodeError:
            if encoding == "ascii":  # must be wrong, because ascii wouldn't
                # cause errors...
                encoding = "utf-8"
            print_error("RBC ERROR: cannot convert to utf-8 from claimed " + encoding)

            try:
                s = string.decode(encoding, errors="replace")
            except UnicodeDecodeError:
                print_error(
                    "RBC ERROR: cannot convert to utf-8 from claimed " + encoding
                )
        return s


def pdf_to_txt(filename, textfile):
    if (
        subprocess.call(
            ["pdftotext", "-l", "10", filename, textfile],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        != 0
    ):
        print_error("Failed to convert pdf to txt: " + filename)


def doc_to_txt(filename, textfile):
    ret = subprocess.call(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "txt:Text (encoded):UTF8",
            "--outdir",
            Path(textfile).parent,
            filename,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    if ret != 0 or Path(textfile).is_file:
        print_error("Failed to convert doc to txt: " + filename)


def tar_to_txt(filename, textfile):
    """Extract list of files"""

    if os.system("tar -t -f %s > %s" % (filename, textfile)) != 0:
        print_error("Failed to convert tar to txt: " + filename)


def zip_to_txt(filename, textfile):
    """Extract list of files

    And write date of first file on first line"""

    if zipfile.is_zipfile(filename):
        z = zipfile.ZipFile(filename)
        l = z.namelist()
        l = [to_utf8(n) for n in l]
        if not l == []:
            date = z.getinfo(l[0]).date_time
            with codecs.open(textfile, "w", encoding="utf-8") as f:
                f.write(l[0] + " %u/%u/%u\n" % (date[0], date[1], date[2]))
                f.write("\n".join(l))  # TODO only write MAX_LINES
        else:
            print_error(
                "Failed to convert zip to txt (possibly empty zipfile): " + filename
            )
            return ""
    else:
        print_error(
            "Failed to convert zip to txt (possibly not a zipfile): " + filename
        )
        return ""


def txt_to_txt(filename, textfile):
    shutil.copyfile(filename, textfile)


def mbox_to_txt(filename, textfile):
    """Insert a date at the start of the file"""

    date = ""
    with open(filename, "tr", encoding="utf-8") as f:
        for line in f:
            line = to_utf8(line)
            if line.startswith("Date: "):
                date = line
                break

    # TODO  only copy MAX_LINES
    with open(filename, "tr", encoding="utf-8") as infile, open(
        textfile, "tw", encoding="utf-8"
    ) as outfile:
        outfile.write("MailBox %s\n" % date)
        outfile.writelines(infile.readlines())
        # doing this we also convert the various line feeds into standard '\n'
        # which a simple os.system('cat ' + filename + " >> " + textfile)
        # would not do.


def ods_to_txt(filename, textfile):
    print_debug("filename:", filename)
    print_debug("textfile:", textfile)
    print_debug("tempdir:", tempdir)
    ret = subprocess.call(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "csv",
            "--outdir",
            tempdir,
            filename,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    outfile = tempdir + "/" + Path(filename).stem + ".csv"
    if ret == 0 and Path(outfile).is_file:
        shutil.copyfile(outfile, textfile)
    else:
        print_error("Failed to convert to csv: " + filename)


def pandoc_to_txt(filename, textfile):
    print_debug("Converting %s to %s using pandoc" % (filename, textfile))
    if (
        subprocess.call(
            ["pandoc", "-o", textfile, filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        != 0
    ):
        print_error("Failed to convert to txt: " + filename)


def ppt_to_txt(filename, textfile):
    # https://wiki.openoffice.org/wiki/Documentation/DevGuide/Spreadsheets/Filter_Options#Filter_Options_for_the_CSV_Filter

    temppdf = tempdir + "/" + Path(filename).stem + ".pdf"
    ret = subprocess.call(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            Path(temppdf).parent,
            filename,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    pdf_to_txt(temppdf, textfile)


def file_to_txt(filename, textfile):
    extension = Path(filename).suffix

    if extension in [".pdf", ".ai"]:
        pdf_to_txt(filename, textfile)
    elif extension == ".doc":
        doc_to_txt(filename, textfile)
    elif extension == ".tar":
        tar_to_txt(filename, textfile)
    elif extension == ".zip":
        zip_to_txt(filename, textfile)
    elif extension == ".txt":
        txt_to_txt(filename, textfile)
    elif extension == ".mbox":
        mbox_to_txt(filename, textfile)
    elif extension in [".ods", ".xls", ".xlsx", ".csv"]:
        ods_to_txt(filename, textfile)
    elif extension in [".docx", ".docm", ".html", ".rtf", ".odt"]:
        pandoc_to_txt(filename, textfile)
    elif extension in [".ppt", ".pptx", ".odg"]:
        ppt_to_txt(filename, textfile)
    else:
        print_debug("Filetype %s not supported" % extension)
        return None


def title_from_txt(textfile):
    """Return probable title in a pure text file, or None"""
    if textfile is None or not os.path.isfile(textfile):
        return None

    print_debug("Examining " + textfile)
    # we start by reading the first N=12 lines with more than X=50 alphanumeric
    # chars, as the title is often there.
    with open(textfile, "rt", encoding="utf-8") as f:
        ascii_count = 0
        i = 0
        accum = ""
        try:
            for line in f:
                i += 1
                line = to_utf8(line.strip())
                print_debug(i, ascii_count, line)
                line = re.sub(r" (\w) ", r"\1", line)  # "S a l u t " --> "Salut "
                line = line.replace("…", "")
                line = re.sub(r"--+", "-", line)
                line = re.sub(r"\.\.+", ".", line)
                line = re.sub(r"\s\s+", " ", line)
                nascii = len(re.sub(r"[^\w]", "", line))
                if nascii > 40:  # then we keep only this one
                    print_debug(line)
                    return line
                else:
                    ascii_count += nascii
                    line = line if i == 1 else " " + line
                    accum += line
                    if ascii_count > 50:  # X=50. we return the accumulated lines
                        print_debug(accum)
                        return accum
                if i > 12:  # N=12, ok  ??
                    break
        except UnicodeDecodeError:
            print_error("We tried (literally ...)")
            return None

    print_debug("Trying to find another line...")
    # we search for a line with a 4-digit number that could be a year
    # because years often appear in a title.
    with open(textfile, "rt", encoding="utf-8") as f:
        for line in f:
            line = to_utf8(line.strip())
            years = re.search(r"\b(19|20)\d{2}\b", line)  # year 19xx or 20xx
            if years is not None:
                print_debug(line)  # TODO test if year is within reasonable range
                y = int(years.group(0))
                if y >= MIN_YEAR:  # we don't impose y <= MAKE_DATE.year because
                    # even a future date can be common in a
                    # title.
                    return line
    return None


def get_tag(tag, filename):
    """Get string tag, or None"""

    # without the exiftool binding, one could do instead, for instance:
    # title = subprocess.check_output(["exiftool", "-Title", "-s",  "-S",  filename])
    try:
        dic = et.get_tags(filename, tags=[tag])[0]
    except exiftool.exceptions.ExifToolExecuteError:
        print_debug("ExifToolExecuteError")
        return None
    src = dic.pop("SourceFile")
    print_debug("Tag src = " + src)
    values = []
    for k, v in dic.items():
        values.append(v)
    if values == []:
        print_debug("Cannot get tag [%s]" % tag)
        return None
    else:
        if len(values) > 1:
            print_debug("EXIF: multiplies values for [%s]" % tag)
            print_debug(values)
        return str(values[0])


def find_date_string(filename):
    """Try to guess the date"""

    # do NOT use FileModifyDate, this was probably reset when
    # recovering data by photorec
    extension = Path(filename).suffix
    search_tags = ["ModifyDate", "CreateDate", "CreationDate"]
    desperate_search_tags = ["FileModifyDate"]
    if extension in [".pdf", ".ai"]:
        search_tags.insert(0, "PDF:ModifyDate")  # see below why
    if extension == ".zip":
        search_tags.append("ZipModifyDate")
    elif extension in [".ods", ".odt"]:
        search_tags.append("Date")
        search_tags.append("Creation-date")
        # TODO add more tags
    exifdates = []
    # for easier debugging we first print all the date tags we consider:
    for tag in search_tags + desperate_search_tags:
        print_debug(tag)
        d = get_tag(tag, filename)
        if d is not None:
            print_debug(tag + "=" + d)
            exifdates.append(d)
    # and now we chose the first valid date:
    for d in exifdates:
        date = None
        for pattern in ["%Y:%m:%d", "%d/%m/%y", "%d/%m/%Y", "%d %B %Y"]:
            # I don't know why for test/recup_dir.2/f26378280.ai we get
            # "CreateDate=09/01/17 12:23"
            # this is due to the python exiftool binding, from the command line this is ok
            # exiftool -d "%Y:%m:%d" -CreateDate -s -S test/recup_dir.2/f26378280.ai
            # To show why the error occurs, see:
            # exiftool -d "%Y:%m:%d" -time:all -a -G0:1 -s test/recup_dir.2/f26378280.ai
            # [File:System]   FileModifyDate                  : 2018:11:16
            # [File:System]   FileAccessDate                  : 2018:12:10
            # [File:System]   FileInodeChangeDate             : 2018:12:05
            # [XMP:XMP-xmp]   MetadataDate                    : 2017:01:09
            # [XMP:XMP-xmp]   ModifyDate                      : 2017:01:09
            # [XMP:XMP-xmp]   CreateDate                      : 2017:01:09
            # [XMP:XMP-xmpMM] HistoryWhen                     : 2017:01:09
            # [PostScript]    CreateDate                      : 09/01/17 12:23
            # [PDF]           CreateDate                      : 2017:01:09
            # [PDF]           ModifyDate                      : 2017:01:09

            try:
                date = datetime.datetime.strptime(d.split(" ")[0], pattern)
                break
            except ValueError:
                print_debug("RBC ERROR: strptime")
        if date is not None:
            return "_" + date.strftime("%Y-%m-%d")
    return ""


def find_better_filename(filepath):
    filepath = str(filepath)

    base = Path(filepath).stem
    suffix = Path(filepath).suffix
    numbers = len("".join(re.findall(r"\d+", base)))
    if len(base) - numbers >= 2:
        prefix = base + "_"
        # if the original filename is not full of number, it is probably best
        # to keep it
    else:
        print_debug("We discard the original filename [%s]" % base)
        prefix = ""
    date = find_date_string(filepath)
    title = get_tag("Title", filepath)
    if title is not None and len(title) >= 3:
        title = get_valid_filename(title)
        print_debug("Title=" + title)
        if title in filepath:
            print_debug("Title is already in filename: we don't modify much.")
            return Path(filepath).stem + date + suffix
        else:
            return prefix + title + date + suffix
    else:
        print_debug("No Title tag, we try scanning the text.")

        exif_info = ""
        textfile = tempdir + "/temp.txt"
        file_to_txt(filepath, textfile)
        title = title_from_txt(textfile)
        if os.path.isfile(textfile):
            os.remove(textfile)

        if title is None:
            title = ""
            
        for tagLists in [
            ["Author", "Artist", "AlbumArtist", "Model", "Make", "Creator"],
            ["Album", "AlbumTitle"]
        ]:
            for tag in tagLists:
                new_exif_info = get_tag(tag, filepath)
                if new_exif_info is not None:
                    if tag == "Creator":
                        new_exif_info = new_exif_info[:20]
                    exif_info += "_" + new_exif_info
                    break

        new_title = title + exif_info

        if new_title == "" and prefix == "":
            print_debug("Could not find any content. Using original file name")
            prefix = base

        new_filename = prefix + get_valid_filename(new_title) + date + suffix
        print_debug("New filename:", new_filename)
        return new_filename


def find_better_filepath(filepath):
    filename = find_better_filename(filepath)
    name = Path(filename).stem
    suffix = Path(filename).suffix

    i = 1
    while True:
        current_suffix = suffix if i == 1 else "_" + str(i) + suffix
        new_filepath = str(Path(filepath).parent) + "/" + name + current_suffix
        if not os.path.isfile(new_filepath):
            return new_filepath

        i += 1


if __name__ == "__main__":
    rootdir = Path(sys.argv[1])
    # Return a list of regular files only, not directories
    file_list = [f for f in rootdir.glob("**/*") if f.is_file()]
    for file in file_list:
        # print the file name
        # if "xls" in str(file):
        #     continue
        for allowed in ["jpg"]:
            if allowed in str(file):
                print(Path(file).name)
                new_path = find_better_filepath(file)
                print("   ->", Path(new_path).name)
                # os.system(f"exiftool {file}")


# print("<\n", find_better_filename("./pdf.pdf"), "\n>")
# print("<\n", find_better_filename("./txt.txt"), "\n>")
# print("<\n", find_better_filename("./ppt.ppt"), "\n>")
# print("<\n", find_better_filename("./docx.docx"), "\n>")
# print("<\n", find_better_filename("./ods.ods"), "\n>")
# print("<\n", find_better_filename("./tar.tar"), "\n>")
# print("<\n", find_better_filename("./zip.zip"), "\n>")
