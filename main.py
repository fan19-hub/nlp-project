import json
from imgCaption import img2txt
from kg_generate_and_compare import kg_generate_and_compare
from zero_shot_prediction import zero_shot
from tool_learning import search

# mode
zero_shot_mode = True

# print the result
view = True

# automatic resume
resume = True

# dataset (twitter or weibo)
data_name = 'twitter'

# using image caption cache
using_cache = True

# max retry times
max_retry = 2

# tool learning
tool_learning = False

# image caption cache file name
image_caption_cache_name = 'image_captioning_cache.json'
tool_learning_cache_name = 'tool_learning_cache.json'

# input data file name
if data_name == 'twitter':
    input_file = 'test_twitter.json'
elif data_name == 'weibo':
    input_file = 'test.json'

# output file names
output_score = 'results'
output_result = 'kg_final_output'

if __name__ == '__main__':
    # Open the JSON file
    print('View:{}\nResume:{}\nUsing cache:{}\nMax retry:{}\nInput file:{}\nOutput score:{}\nOutput result:{}\n'
          .format(view, resume, using_cache, max_retry, input_file, output_score, output_result))

    with open(input_file, encoding='utf-8') as file:
        data = json.load(file)

    image_captioning_cache = {}
    tool_learning_cache = {}

    if using_cache:
        try:
            with open(image_caption_cache_name, encoding='utf-8') as f:
                image_captioning_cache = json.load(f)
            print('Using image captioning cache')
        except FileNotFoundError:
            image_captioning_cache = {}
            print('No image captioning cache found')
        try:
            with open(tool_learning_cache_name, encoding='utf-8') as f:
                tool_learning_cache = json.load(f)
            print('Using tool learning cache')
        except FileNotFoundError:
            tool_learning_cache = {}
            print('No tool learning cache found')

    if resume:
        with open(output_score, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            labels = []
            for char in lines[1]:
                if char.isdigit():
                    labels.append(int(char))
            pred_labels = []
            for char in lines[3]:
                if char.isdigit():
                    pred_labels.append(int(char))
        results = []
        data = data[len(labels):]
        print('Resuming from index', len(labels))
    else:
        results = []
        pred_labels = []
        labels = []
        print('Starting from index 0')
        with open(output_score, 'w', encoding='utf-8') as f:
            f.write('Labels:\n{}\nPredictions:\n{}\n'.format(labels, pred_labels))
        with open(output_result, 'w', encoding='utf-8') as f:
            f.write('')

    for item in data:
        print('Processing index {}/{}'.format(len(labels), len(data)))
        # read
        url = item["image_url"]
        text = item["original_post"]
        label = item["label"]

        # tool learning
        if tool_learning:
            print('Tool learning...')
            use_cache_flag = False
            if using_cache:
                if text in tool_learning_cache:
                    tool_learning_text = tool_learning_cache[text]
                    use_cache_flag = True

            if not use_cache_flag:
                for i in range(max_retry):
                    try:
                        tool_learning_text = search(text)
                        if tool_learning_text is None:
                            print('Tool learning error, retrying...')
                            continue
                        break
                    except:
                        print('Tool learning error, retrying...')
                else:
                    print('Tool learning error, skipping...')
                    continue
                if using_cache:
                    tool_learning_cache[text] = tool_learning_text
                    with open(tool_learning_cache_name, 'w', encoding='utf-8') as f:
                        json.dump(tool_learning_cache, f, ensure_ascii=False)
        else:
            tool_learning_text = None

        use_cache_flag = False
        # image captioning
        if using_cache:
            if url in image_captioning_cache:
                image_text = image_captioning_cache[url]
                if 'sorry' not in image_text and 'Sorry' not in image_text:
                    use_cache_flag = True

        if not use_cache_flag:
            for i in range(max_retry):
                try:
                    image_text = img2txt(url, data_name)
                    if 'sorry' in image_text.lower():
                        print('Image captioning error, retrying...')
                        continue
                    break
                except:
                    print('Image captioning error, retrying...')
            else:
                print('Image captioning error, skipping...')
                continue
            if using_cache:
                image_captioning_cache[url] = image_text
                with open(image_caption_cache_name, 'w', encoding='utf-8') as f:
                    json.dump(image_captioning_cache, f)

        # kg
        for i in range(max_retry):
            try:
                if zero_shot_mode:
                    kg1, kg2, kg3, prob, explain = zero_shot(text, image_text, tool_learning_text)
                else:
                    kg1, kg2, kg3, prob, explain = kg_generate_and_compare(text, image_text, tool_learning_text)
                break
            except:
                print('KG error, retrying...')
        else:
            print('KG error, skipping...')
            continue

        if prob < 0.6:
            pred_label = 0
        else:
            pred_label = 1

        pred_labels.append(pred_label)
        results.append(explain)
        labels.append(label)

        if view:
            print('Text:\n{}\nImage:\n{}\nTool:\n{}\nKG1:\n{}\nKG2:\n{}\nKG3:\n{}\nLabel: {}\nPrediction: {}\n'
                  .format(text, image_text, tool_learning_text, kg1, kg2, kg3, label, explain))

        with open(output_score, 'w', encoding='utf-8') as f:
            f.write('Labels:\n{}\nPredictions:\n{}\n'.format(labels, pred_labels))
        with open(output_result, 'a', encoding='utf-8') as f:
            f.write('Text:\n{}\nImage:\n{}\nTool:\n{}\nKG1:\n{}\nKG2:\n{}\nKG3:\n{}\nLabel: {}\nPrediction: {}\n'
                    .format(text, image_text, tool_learning_text, kg1, kg2, kg3, label, explain))

    print('Labels:', labels)
    print('Predictions:', pred_labels)

    # overall accuracy
    accuracy = sum((l == p) for l, p in zip(labels, pred_labels)) / len(labels)
    print('Accuracy:', accuracy)

    # rumor version
    rumor_labels = labels
    rumor_pred_labels = pred_labels

    # non-rumor version
    non_rumor_labels = [1 - l for l in labels]
    non_rumor_pred_labels = [1 - p for p in pred_labels]

    rumor_true_positives = sum((l == 1 and p == 1) for l, p in zip(rumor_labels, rumor_pred_labels))
    rumor_false_positives = sum((l == 0 and p == 1) for l, p in zip(rumor_labels, rumor_pred_labels))
    rumor_false_negatives = sum((l == 1 and p == 0) for l, p in zip(rumor_labels, rumor_pred_labels))
    rumor_true_negatives = sum((l == 0 and p == 0) for l, p in zip(rumor_labels, rumor_pred_labels))

    rumor_precision = rumor_true_positives / (rumor_true_positives + rumor_false_positives)
    rumor_recall = rumor_true_positives / (rumor_true_positives + rumor_false_negatives)
    rumor_f1 = 2 * rumor_precision * rumor_recall / (rumor_precision + rumor_recall)

    non_rumor_true_positives = sum((l == 1 and p == 1) for l, p in zip(non_rumor_labels, non_rumor_pred_labels))
    non_rumor_false_positives = sum((l == 0 and p == 1) for l, p in zip(non_rumor_labels, non_rumor_pred_labels))
    non_rumor_false_negatives = sum((l == 1 and p == 0) for l, p in zip(non_rumor_labels, non_rumor_pred_labels))
    non_rumor_true_negatives = sum((l == 0 and p == 0) for l, p in zip(non_rumor_labels, non_rumor_pred_labels))

    non_rumor_precision = non_rumor_true_positives / (non_rumor_true_positives + non_rumor_false_positives)
    non_rumor_recall = non_rumor_true_positives / (non_rumor_true_positives + non_rumor_false_negatives)
    non_rumor_f1 = 2 * non_rumor_precision * non_rumor_recall / (non_rumor_precision + non_rumor_recall)

    with open(output_score, 'w', encoding='utf-8') as f:
        f.write('Labels:\n{}\nPredictions:\n{}\n\n'.format(labels, pred_labels))

        f.write('Accuracy: {}\n\n'.format(accuracy))

        f.write('Rumor Section:\n')
        f.write('True positives: {}\n'.format(rumor_true_positives))
        f.write('False positives: {}\n'.format(rumor_false_positives))
        f.write('False negatives: {}\n'.format(rumor_false_negatives))
        f.write('True negatives: {}\n'.format(rumor_true_negatives))
        f.write('Precision: {}\n'.format(rumor_precision))
        f.write('Recall: {}\n'.format(rumor_recall))
        f.write('F1 Score: {}\n\n'.format(rumor_f1))

        f.write('Non-rumor Section:\n')
        f.write('True positives: {}\n'.format(non_rumor_true_positives))
        f.write('False positives: {}\n'.format(non_rumor_false_positives))
        f.write('False negatives: {}\n'.format(non_rumor_false_negatives))
        f.write('True negatives: {}\n'.format(non_rumor_true_negatives))
        f.write('Precision: {}\n'.format(non_rumor_precision))
        f.write('Recall: {}\n'.format(non_rumor_recall))
        f.write('F1 Score: {}\n\n'.format(non_rumor_f1))
