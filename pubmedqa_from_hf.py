import asyncio

from datasets import load_dataset
import pandas as pd

async def get_pubmedqa():
    # load dataset
    dataset = load_dataset("qiaojin/PubMedQA", 'pqa_artificial')

    # load the train split of the dataset
    train_data = dataset["train"]

    # convert the train data into pandas data frame
    df = pd.DataFrame(train_data)

    # save the data to csv
    df.to_csv("pubmedqa.csv", index=False)

asyncio.run(get_pubmedqa())