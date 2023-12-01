import openai
import os
from openai import OpenAI
from config import OPENAI_KEY
openai.api_key = os.getenv("OPENAI_API_KEY")
# openai.api_key = OPENAI_KEY

client = OpenAI()


def kg_generate_and_compare(text, image_text, tool_learning_text=None, kg_generate_prompt_path='kg_gen_prompt.md',
                            kg_compare_prompt_path='kg_comp_prompt.md', kg_tool_comp_prompt_path='kg_toollearning_comp_prompt.md'):
    with open(kg_generate_prompt_path, 'r', encoding='utf-8') as f:
        gen_prompt = f.read()
    with open(kg_compare_prompt_path, 'r', encoding='utf-8') as f:
        comp_prompt = f.read()
    with open(kg_tool_comp_prompt_path, 'r', encoding='utf-8') as f:
        tool_comp_prompt = f.read()

    print('Generating KG...')
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": "You are an expert in Knowledge Graph generation"},
            {"role": "user",
             "content": gen_prompt.format(TEXT=text, IMAGETEXT=image_text, TOOL=tool_learning_text if tool_learning_text else 'No third text. Please ignore.')}
        ]
    )
    kg = completion.choices[0].message.content
    kg1 = kg.split('---')[0]
    kg2 = kg.split('---')[1]
    if tool_learning_text:
        kg3 = kg.split('---')[2]
    else:
        kg3 = None

    print('Comparing...')
    p = comp_prompt if tool_learning_text is None else tool_comp_prompt
    original_text = 'Original text for the first KG:\n' + text + '\nOriginal text for the second KG:\n' + image_text + '\n'
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system",
             "content": "You are an expert in Knowledge Graph comparison"},
            {"role": "user",
             "content": p.format(KG=kg, ORIGINALTEXT=original_text)}
        ],
        temperature=0.05,
    )
    predicted_label = float(completion.choices[0].message.content.split('\n')[0].strip())
    return kg1, kg2, kg3, predicted_label, completion.choices[0].message.content
