import shutil
import os
import re
from collections import defaultdict
import textgrid as tg
import sys
import pandas as pd
import tgt


remove_regex = re.compile(r"<<?[A-Z@]+|[A-Z@]+>?>|\(?\((?!H)[A-Z\-]+\)\)?")
sub_regex = re.compile(r"\[[\d!]?|[\d!]?\]|\.{2,3}|[<>!=_%+;`\/\\&~]")
breath_regex = re.compile(r"\(H+x*\)")
laugh_regex = re.compile(r"@+")
BREATH_WORD_SB = ""
LAUGH_WORD_SB = ""

def get_utterances_p2_4(file, textgrid_file):
    """ 
    read utterance from .trn file and write them to textgrid format
    collapses utterances with <.15s pauses between them into 1 utterance
    textgrid tiers are based on speakers (each speaker |-> 1 tier). For textgrids in Part1
    
    Parameters
    ----------
    file : str
        path to .trn file
    textgrid_file : str
        path to textgrid file
    """

    with open(file, encoding='ISO-8859-15') as f1:
        lines = f1.readlines()
    
    ordered_tups = []
    speakers = defaultdict(list)
    skipped = 0

    lines_wo_empty = []
    for line in lines:
        if line.strip() == "":
            continue
        lines_wo_empty.append(line)
    lines = lines_wo_empty

    for i,line in enumerate(lines):
        if line.strip() == "":
            continue
        if '\x00' in line:
            line = "c".join(line.split('\x00'))
        splitline = re.split("\t+", line)

        start = splitline[0]
        end = splitline[1]
        if splitline[2].strip().endswith(":"):
            speaker = splitline[2]
            try:
                label = splitline[3]
            except IndexError:
                label = ""
        else:
            speaker = ordered_tups[i-1][2]
            try:
                label = splitline[2]
            except IndexError:
                label = ""

        label = preprocess_text_part_1(label)

        speaker = re.sub("[:\s]","",speaker)
        speaker = re.sub(">env","env", speaker.lower())
        # if label not in ["", " ", None]:
        ordered_tups.append( (start, end, speaker, label) )
        speakers[speaker.lower()].append( (start, end, label))
        
    speakers = clean(speakers)

    textgrid = tg.TextGrid()
    for i,speaker in enumerate(speakers.keys()):
        tier = tg.IntervalTier(name = "{} - utterance".format(speaker.strip()))
        for j, tup in enumerate(speakers[speaker]):
            try:
                if float(tup[0]) == float(tup[1]):
                    continue
            except ValueError:
                pass
            try:
                tier.add(float(tup[0]), float(tup[1]), tup[2].strip())
            except ValueError:
                try:
                    previous = tier[-1]
                except IndexError:
                    skipped +=1
                    continue
                previous_end = previous.maxTime
                difference = previous.maxTime - float(tup[0])
                if difference < 0 :
                    skipped +=1
                    continue
                if float(tup[0]) + difference == float(tup[1]):
                    skipped +=1
                    continue
                tier.add(float(tup[0]) + difference, float(tup[1]), tup[2].strip())
        if len(tier.intervals)>0:
            textgrid.append(tier)
    
    textgrid.write(textgrid_file)

    print("skipped: {}".format(skipped))
    return ordered_tups





def get_utterances_p1(file, textgrid_file):
    """ 
    read utterance from .trn file and write them to textgrid format
    collapses utterances with <.15s pauses between them into 1 utterance
    textgrid tiers are based on speakers (each speaker |-> 1 tier). For textgrids in Part1
    
    Parameters
    ----------
    file : str
        path to .trn file
    textgrid_file : str
        path to textgrid file
    """

    with open(file, encoding='ISO-8859-15') as f1:
        lines = f1.readlines()
    
    ordered_tups = []
    speakers = defaultdict(list)
    skipped = 0
    
    for i,line in enumerate(lines):
        try:
            splitline = re.split("\t+", line)
            subsplit = re.split("\s",splitline[0])

            start = subsplit[0]
            end = subsplit[1]
            speaker = splitline[1]

            if re.match("\s+", speaker) is not None:
                speaker = ordered_tups[i-1][2]
            try:
                label = splitline[2] 
            except:
                label = ""
            
            # label = re.sub("[=_%]","", label)
            
        except IndexError:
            try:
                splitline = re.split("\t+", line)

                start = splitline[0]
                end = splitline[1]
                speaker = splitline[2]
                if re.match("\s+", speaker) is not None:
                    speaker = ordered_tups[i-1][2]
                try:
                    label = splitline[2]
                except:
                    label = ""
                
            except IndexError:
                total_split = re.split("\s", line)
                start = total_split[0]
                end = total_split[1]
                speaker = total_split[2]
                if re.match("\s+", speaker) is not None or speaker is None:
                    speaker = ordered_tups[i-1][2]
                label = " ".join(total_split[3:])

        label = preprocess_text(label)

        speaker = re.sub("[:\s]","",speaker)
        speaker = re.sub(">env","env", speaker.lower())
        # if label not in ["", " ", None]:
        ordered_tups.append( (start, end, speaker, label) )
        speakers[speaker.lower()].append( (start, end, label))


    speakers = clean(speakers)

    textgrid = tg.TextGrid()
    for i,speaker in enumerate(speakers.keys()):
        tier = tg.IntervalTier(name = "{} - utterance".format(speaker.strip()))
        for j, tup in enumerate(speakers[speaker]):
            try:
                if float(tup[0]) == float(tup[1]):
                    continue
            except ValueError:
                pass
            try:
                tier.add(float(tup[0]), float(tup[1]), tup[2].strip())
            except ValueError:
                try:
                    previous = tier[-1]
                except IndexError:
                    skipped +=1
                    continue
                previous_end = previous.maxTime
                difference = previous.maxTime - float(tup[0])
                if difference < 0 :
                    skipped +=1
                    continue
                # if float(tup[0]) + difference == float(tup[1]):
                #     print("overlap")
                #     print(speaker)
                #     print(tup)
                #     skipped +=1
                #     continue

                tier.add(float(tup[0]) + difference, float(tup[1]), tup[2].strip())
        if len(tier.intervals)>0:
            textgrid.append(tier)


    textgrid.write(textgrid_file)

    print("skipped: {}".format(skipped))
    return ordered_tups


def preprocess_text(label):
    label = remove_regex.sub("", label)
    label = sub_regex.sub("", label)
    label = breath_regex.sub(BREATH_WORD_SB, label)
    label = laugh_regex.sub(LAUGH_WORD_SB, label)
    label = re.sub("((?<![a-zA-Z])[a-zA-Z]-)", r"[\1]", label)
    label = label.strip()
    return label

def preprocess_text_part_1(label):
    label = remove_regex.sub("", label)
    label = sub_regex.sub("", label)
    label = breath_regex.sub(BREATH_WORD_SB, label)
    label = laugh_regex.sub(LAUGH_WORD_SB, label)
    label = re.sub("([a-zA-Z]-)", r"[\1]", label)
    label = label.strip()
    return label

def clean(speakers):
    """
    clean the speakers dictionary
    this is where the collapsing of utterances takes place
    default boundary is .15 seconds

    Parameters
    ----------
    speakers : defaultdict(list)
        dictionary of speakers and their utterances as separated in .trn file

    Returns
    -------
    new_speakers : defaultdict(list)
        same keys as input, but the utterances for each speaker are compressed
    """

    new_speakers = defaultdict(list)
    for speaker,tups in speakers.items():
        new_tups = []
        i =1
        new_tup = list(tups[0])
        while i < len(tups):
            old_tup = list(tups[i-1])
            current_tup = list(tups[i])
            # if difference between new and old < .15 collapse
            try:
                if float(current_tup[0]) - float(old_tup[1])  < .15:
                    new_tup[1] = current_tup[1] 
                    new_tup[2] = new_tup[2].strip()+  " " + current_tup[2].strip()
                    # print("new tup: ", new_tup[2])
                    # i+=1
                else:
                    new_tups.append(new_tup)
                    new_tup = list(current_tup)
            except ValueError:
                # fix this later!
                print(tups[i])
            #otherwise add the current and start over
            
            i+=1

        new_speakers[speaker] = new_tups
    return new_speakers


def addition_processing_for_ordered_tuples(df_ot):
    # get word info (with turn and IU tags)

    all_words = df_ot.text.str.strip(to_strip=",.?-").str.split().explode() # removes prototype (Maybe we need that inforamation in some way)

    df_words = all_words.rename("word").to_frame().join(df_ot).reset_index().rename(columns={"index": "iu_id"})

    df_words = df_words[~df_words.word.str.contains("\[").astype(bool)]  # remove words with '['
    df_words = df_words[~df_words.word.str.contains("#").astype(bool)]  # remove words with '#'
    df_words = df_words[~df_words.word.isin(['-', '--']).astype(bool)]  # remove '-' and '--' (boundary specification?)

    df_words["is_iu_start"] = ~df_words.iu_id.duplicated(keep="first")
    df_words["turn_id"] = (df_words.speaker_id != df_words.speaker_id.shift()).cumsum()

    df_words["word"] = df_words["word"].str.lower()

    # remove overlapping IUs

    df_ius = df_words.groupby("iu_id")[['xmin', 'xmax']].first()
    is_overlap = (df_ius.xmin < df_ius.xmax.shift())
    is_overlap = is_overlap | is_overlap.shift(-1)

    non_overlapping_iu_ids = is_overlap[~is_overlap].index

    df_words_wo_overlap = df_words[df_words.iu_id.isin(non_overlapping_iu_ids)]
    return df_words_wo_overlap


def df_to_tg(df: pd.DataFrame) -> tgt.TextGrid:
    necessary_cols = {"xmin", "xmax", "text", "tier_name"}
    missing_columns = necessary_cols - (set(df) & necessary_cols)
    assert len(missing_columns) == 0, f"df is missing the columns {missing_columns}"

    df = df.astype({"xmin":"float","xmax":"float"})

    tg = tgt.TextGrid()
    for name in df["tier_name"].unique():
        df_sel = df[df["tier_name"] == name]
        objects = (
            df_sel.apply(
                lambda df_: tgt.Interval(df_["xmin"], df_["xmax"], df_["text"]), axis=1
            )
            .tolist()
        )
        tg.add_tier(
            tgt.IntervalTier(
                df["xmin"].iloc[0], df["xmax"].iloc[-1], name=name, objects=objects
            )
        )
    return tg


def from_df_words_to_mfa_input(df_words) -> tgt.TextGrid:
    df_mfa_input = df_words.groupby("iu_id").agg(
        {'xmin': "first",
         'xmax': "first",
         'speaker_id': "first",
         'word': lambda x: " ".join(x),
         }
    )
    df_mfa_input = df_mfa_input.rename(columns={
        "speaker_id": "tier_name",
        'word': "text",
    })
    tg_mfa_input = df_to_tg(df_mfa_input)
    return tg_mfa_input


def convert_all(source_dir, destination_dir, exclude = tuple(), move_wav = False):
    """
    walk throught source dir, convert all .trn files to .textgrids
    copy wav files to destination dir
    assumes .wav and .trn files share a filename and are in the same directory

    Parameters
    ----------
    source_dir : str
        the location of .trn and .wav files
    destination_dir : str
        the desired location for the resulting textgrids/.wav files
    """

    for root, dirs, files in os.walk(source_dir, topdown = True):
        for file in files:
            if file.endswith('.trn'):
                just_name = file.split(".")[0]
                num = "".join(just_name[-3:])
                print(num)
                if str(int(num)) not in exclude:
                    if move_wav:
                        wav_name = just_name+ ".wav"
                        shutil.copy(os.path.join(root,wav_name), os.path.join(destination_dir, wav_name))
                        print('copied')

                    output_path = os.path.join(destination_dir, just_name+".TextGrid")
                    if "Part1" in root:
                        ot = get_utterances_p1(os.path.join(root,file), output_path)
                    else:
                        ot = get_utterances_p2_4(os.path.join(root,file), output_path)
                    df_ot = pd.DataFrame(ot)
                    df_ot.columns = ["xmin", "xmax", "speaker_id", "text"]
                    df_ot = df_ot.dropna()

                    df_words = addition_processing_for_ordered_tuples(df_ot)
                    df_words.to_csv(os.path.join(destination_dir, just_name+".csv"))
                    tg_mfa_input = from_df_words_to_mfa_input(df_words)
                    tgt.write_to_file(
                        tg_mfa_input,
                        output_path,
                        format='long',
                        encoding='utf-8',
                    )


                # def get_words(source, dictionary):
#     words = set()
#     for root, dirs, files in os.walk(source, topdown = True):
#         for file in files:
#             if file.endswith('.trn'):
#                 just_name = file.split(".")[0]
#                 num = "".join(just_name[-3:])
#                 word_tup = get_utterances_p1(os.path.join(root,file), os.path.join("", just_name+".textgrid"))

#                 labels = set([x[3].strip() for x in word_tup])
#                 list_words = [re.split("\s", x) for x in labels]
#                 for line in list_words:
#                     words |= set([re.sub("[\.,?!]","",x )for  x in line])

#     with open(dictionary) as f1:
#         dict_words = set([re.split("\s+",x)[0].lower().strip() for x in f1.readlines()])

#     new_words = []
#     exclude_regex = re.compile(r"<<.*>?>?|\(\(.*\)?\)?|\([A-Zhx]+\)?|%|\([\.\d]+\)|<.*|.*>")
#     sub_regex = re.compile(r"\[\d|\d\]")
#     sub_regex_2 = re.compile(r"[+=!;`/\&\[\]]")
#     # test clean
#     for word in words:

#         if exclude_regex.search(word.strip()) is None:
#             word = sub_regex.sub("",word)
#             word = sub_regex_2.sub("",word)
#             new_words.append(word.lower())

#     new_words = sorted(set(new_words))

#     oovs = set([x for x in new_words if x not in dict_words])

#     with open("oovs","w") as f2:
#         [f2.write(word.strip()+"\n") for word in sorted(oovs)]


if __name__ == '__main__':
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    exclude = sys.argv[3].split(',')
    print(exclude)
    move_wav = sys.argv[4]
    if move_wav in ["True", True]:
        convert_all(input_dir, output_dir, exclude, True)
    else:
        convert_all(input_dir, output_dir, exclude)

    # get_words("/Volumes/data/corpora/SantaBarbara/Part1/speech", "/Volumes/data/datasets/aligner_benchmarks/LibriSpeech/librispeech-lexicon.txt")


    # convert_all("/Volumes/data/corpora/SantaBarbara/Part1/speech", 
    # "/Volumes/data/corpora/Santa_Barbara_textgrids/Part1")