import os
import designData
from pathlib import Path


def export_data(data: dict, name: str) -> None:

    export = designData.prep_data_for_export(data)
    header = ", ".join([str(i) for i in export.keys()])
    export_str = ", ".join([str(i) for i in export.values()])

    try:
        os.mkdir("./database")
    except FileExistsError:
        pass

    try:
        with open("./database/designdata.csv", mode="r+") as out:
            if header == out.readline(0):
                pass
    except FileNotFoundError:
        with open("./database/designdata.csv", mode="w+") as out:
            out.write(header + "\n")

    with open("./database/designdata.csv", mode="a") as out:
        out.write(export_str + "\n")
        # out.write("\nEND")
    return


def main():
    folders = Path("./")
    for folder in folders.iterdir():
        for files in folder.iterdir():
            if files.suffix == ".txt":
                with open(files, 'r', encoding="utf8") as f:

                    for line in f:
                        if line.startswith('Project ='):
                            name = line[9:-1].strip()
                            break

                    designdata = designData.DesignData(name=name)
                    data = designdata.compute_data()
                    export_data(data=data, name=name)

    return


if __name__ == "__main__":
    main()
