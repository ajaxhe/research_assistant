import configparser
import os
import openai
import pandas as pd
import tiktoken

from openai.embeddings_utils import distances_from_embeddings

config = configparser.ConfigParser()
config.read('default.cfg')
d_conf = config['DEFAULT']

# init openai param
openai.api_type = d_conf['api_type']
openai.api_base = d_conf['api_base'] 
openai.api_version = d_conf['api_version']

max_tokens = int(d_conf['max_tokens'])

# Load the cl100k_base tokenizer which is designed to work with the ada-002 model
tokenizer = tiktoken.get_encoding("cl100k_base")

domain_map = {'qinglian': '腾讯轻联'}

# Function to split the text into chunks of a maximum number of tokens
def split_into_many(text, max_tokens = max_tokens):

    # Split the text into sentences
    sentences = text.split('。')

    # Get the number of tokens for each sentence
    n_tokens = [len(tokenizer.encode(" " + sentence)) for sentence in sentences]

    chunks = []
    tokens_so_far = 0
    chunk = []

    # Loop through the sentences and tokens joined together in a tuple
    for sentence, token in zip(sentences, n_tokens):

        # If the number of tokens so far plus the number of tokens in the current sentence is greater
        # than the max number of tokens, then add the chunk to the list of chunks and reset
        # the chunk and tokens so far
        if tokens_so_far + token > max_tokens:
            chunks.append("。 ".join(chunk) + "。")
            chunk = []
            tokens_so_far = 0

        # If the number of tokens in the current sentence is greater than the max number of
        # tokens, go to the next sentence
        if token > max_tokens:
            continue

        # Otherwise, add the sentence to the chunk and add the number of tokens to the total
        chunk.append(sentence)
        tokens_so_far += token + 1

    # append the last chunk
    if tokens_so_far > 0 and len(chunk) > 0:
        chunks.append("。 ".join(chunk) + "。")


    return chunks



def remove_newlines(serie):
    serie = serie.replace('\n', ' ')
    serie = serie.replace('\\n', ' ')
    serie = serie.replace('  ', ' ')
    serie = serie.replace('  ', ' ')
    return serie


def embedding_text():
    # Create a list to store the text files
    texts=[]

    text_path = d_conf['text_path']
    # Get all the text files in the text directory
    for domain in os.listdir(text_path):
        path_prefix = os.path.join(text_path, domain)
        if not os.path.isdir(path_prefix):
            continue

        for file in os.listdir(path_prefix):
            # Open the file and read the text
            with open(path_prefix + "/" + file, "r") as f:
                text_raw = f.read()
                text = remove_newlines(text_raw)
                url = 'https://'+file[12:-4].replace('_','/')
                p_date = file[:10]
                n_tokens = len(tokenizer.encode(text))
                texts.append( (domain, domain_map[domain], url, p_date, n_tokens, text) )


    shortened = []
    raw_text_num = 0
    split_text_num = 0

    # Loop through the dataframe
    for domain, f_domain, url, p_date, n_tokens, text in texts:
        # If the text is None, go to the next row
        if text is None:
            continue
    
        raw_text_num += 1

        # If the number of tokens is greater than the max number of tokens, split the text into chunks
        meta_info = f"{f_domain}, 发布时间: {p_date}。内容: "
        if n_tokens > max_tokens:
            chunks = split_into_many(text)
            split_text_num += len(chunks)
            shortened.extend([{
                'domain': domain,
                'f_domain': f_domain,
                'url': url,
                'p_date': p_date,
                'n_tokens': len(tokenizer.encode(chunk)),
                'text': meta_info + chunk} for chunk in chunks])
        else:
            # Otherwise, add the text to the list of shortened texts
            split_text_num += 1
            shortened.append({
                'domain': domain,
                'f_domain': f_domain,
                'url': url,
                'p_date': p_date,
                'n_tokens': n_tokens,
                'text': meta_info + text})

    new_df = pd.DataFrame(shortened, columns = ['domain', 'f_domain', 'url', 'p_date', 'n_tokens', 'text'])


    new_df['embeddings'] = new_df.text.apply(
        lambda x: openai.Embedding.create(
            input=x, 
            deployment_id=d_conf['embedding_model_depleyment_id'],
            #engine=embedding_model,
        )['data'][0]['embedding'])


    new_df.index.name = 'id'
    new_df.to_csv(d_conf['csv_file'])

    print(f"raw text num:{raw_text_num}, split text num:{split_text_num}")


if __name__ == '__main__':
    embedding_text()
