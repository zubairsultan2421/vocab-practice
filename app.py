from flask import Flask, render_template_string, request, jsonify
import pandas as pd
import random
import requests
import io
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_dictionary(url):
    logger.debug(f"Attempting to download CSV from {url}")
    try:
        session = requests.Session()
        response = session.get(url, stream=True, allow_redirects=True)
        response.raise_for_status()
        logger.debug(f"Initial response status: {response.status_code}, URL: {response.url}")

        if 'download_warning' in response.url or 'Content-Type' not in response.headers:
            confirm_token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_token = value
                    break
            if confirm_token:
                logger.debug(f"Found confirmation token: {confirm_token}")
                params = {'id': '1ZQWtB1Gk6e1M3QKBsSaNWDqPOcAMocqqs5CDpa8y0o4', 'confirm': confirm_token}
                response = session.get(url, params=params, stream=True, allow_redirects=True)
                response.raise_for_status()
                logger.debug(f"Response after confirmation: {response.status_code}, URL: {response.url}")

        content_type = response.headers.get('content-type', '').lower()
        logger.debug(f"Content-Type: {content_type}")
        if 'text/csv' not in content_type and 'application/csv' not in content_type:
            logger.error("Downloaded content is not a CSV file.")
            return None

        df = pd.read_csv(io.BytesIO(response.content))
        df['dateadded'] = pd.to_datetime(df['dateadded'])
        logger.debug(f"Successfully loaded {len(df)} rows from CSV")
        return df
    except Exception as e:
        logger.error(f"Error in load_dictionary: {str(e)}")
        return None

@app.route('/')
def index():
    logger.info("Received request for index page")
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vocabulary Practice</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 100%; padding: 1rem; }
        @media (min-width: 640px) { .container { max-width: 640px; margin: 0 auto; } }
        .input-field { width: 100%; padding: 0.5rem; margin-top: 0.5rem; border: 1px solid #d1d5db; border-radius: 0.375rem; }
        .btn { background-color: #3b82f6; color: white; padding: 0.5rem 1rem; border-radius: 0.375rem; margin-top: 0.5rem; display: inline-block; }
        .btn:hover { background-color: #2563eb; }
        .hidden { display: none; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto">
        <h1 class="text-2xl font-bold text-center mb-4">Vocabulary Practice</h1>

        <!-- Date Range Input -->
        <div id="dateRangeSection">
            <p class="mb-2">Enter the date range for practice (format: YYYY-MM-DD)</p>
            <input type="date" id="startDate" class="input-field" placeholder="Start date">
            <input type="date" id="endDate" class="input-field" placeholder="End date">
            <button onclick="startPractice()" class="btn">Start Practice</button>
        </div>

        <!-- Practice Section -->
        <div id="practiceSection" class="hidden">
            <p id="wordCount" class="mb-2"></p>
            <div id="wordDisplay" class="mb-4">
                <p id="meaning" class="text-lg"></p>
                <p id="wordType" class="text-sm text-gray-600"></p>
                <input type="text" id="userAnswer" class="input-field" placeholder="Enter the word">
                <button onclick="submitAnswer()" class="btn">Submit</button>
            </div>
            <p id="result" class="mb-2"></p>
            <p id="score" class="font-semibold"></p>
        </div>

        <!-- Completion Section -->
        <div id="completionSection" class="hidden">
            <p id="finalScore" class="text-lg font-semibold mb-2"></p>
            <button onclick="restartPractice()" class="btn">Restart Practice</button>
        </div>
    </div>

    <script>
        let words = [];
        let currentIndex = 0;
        let score = 0;
        let total = 0;

        async function startPractice() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;

            if (!startDate || !endDate) {
                alert('Please enter both start and end dates.');
                return;
            }

            try {
                const response = await fetch(`/get_words?start_date=${startDate}&end_date=${endDate}`);
                const data = await response.json();
                if (data.error) {
                    alert(data.error);
                    return;
                }

                words = data.words;
                if (words.length < 2) {
                    alert('Not enough words in the date range to practice 2 words.');
                    return;
                }

                words = words.sort(() => 0.5 - Math.random()).slice(0, 2); // Randomly select 2 words
                currentIndex = 0;
                score = 0;
                total = 0;

                document.getElementById('dateRangeSection').classList.add('hidden');
                document.getElementById('practiceSection').classList.remove('hidden');
                document.getElementById('wordCount').textContent = `Starting vocabulary practice. You will practice 2 words.`;
                displayWord();
            } catch (error) {
                alert('Error fetching words: ' + error.message);
            }
        }

        function displayWord() {
            if (currentIndex >= words.length) {
                endPractice();
                return;
            }

            const wordData = words[currentIndex];
            document.getElementById('meaning').textContent = `Meaning: ${wordData.meaning}`;
            document.getElementById('wordType').textContent = `(${wordData.type})`;
            document.getElementById('userAnswer').value = '';
            document.getElementById('result').textContent = '';
            document.getElementById('score').textContent = `Current score: ${score}/${total}`;
        }

        function submitAnswer() {
            const userAnswer = document.getElementById('userAnswer').value.trim().toLowerCase();
            const correctWord = words[currentIndex].word.toLowerCase();
            total++;

            if (userAnswer === correctWord) {
                document.getElementById('result').textContent = 'Correct!';
                score++;
            } else {
                document.getElementById('result').textContent = `Wrong. The correct word is: ${words[currentIndex].word}`;
            }

            document.getElementById('score').textContent = `Current score: ${score}/${total}`;
            currentIndex++;
            setTimeout(displayWord, 1000); // Delay to show result before next word
        }

        function endPractice() {
            document.getElementById('practiceSection').classList.add('hidden');
            document.getElementById('completionSection').classList.remove('hidden');
            document.getElementById('finalScore').textContent = `Practice session ended. Final score: ${score}/${total} (${(score/total*100).toFixed(2)}%)`;
        }

        function restartPractice() {
            document.getElementById('completionSection').classList.add('hidden');
            document.getElementById('dateRangeSection').classList.remove('hidden');
            document.getElementById('startDate').value = '';
            document.getElementById('endDate').value = '';
        }
    </script>
</body>
</html>
    ''')

@app.route('/get_words')
def get_words():
    logger.info("Received request for /get_words")
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    logger.debug(f"Start date: {start_date}, End date: {end_date}")

    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except ValueError:
        logger.error("Invalid date format in /get_words")
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'})

    file_url = "https://docs.google.com/spreadsheets/d/1ZQWtB1Gk6e1M3QKBsSaNWDqPOcAMocqqs5CDpa8y0o4/export?format=csv"
    df = load_dictionary(file_url)
    if df is None:
        logger.error("Failed to load dictionary data in /get_words")
        return jsonify({'error': 'Failed to load dictionary data.'})

    mask = (df['dateadded'] >= start_date) & (df['dateadded'] <= end_date)
    practice_words = df[mask]
    logger.debug(f"Filtered {len(practice_words)} words in date range")

    if practice_words.empty:
        logger.warning("No words found in the specified date range")
        return jsonify({'error': 'No words found in the specified date range.'})

    words = practice_words[['word', 'type', 'meaning']].to_dict('records')
    logger.info(f"Returning {len(words)} words")
    return jsonify({'words': words})

if __name__ == "__main__":
    logger.info("Starting Flask server on port 5000")
    app.run(debug=True, host='0.0.0.0', port=5000)