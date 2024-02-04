const video = document.getElementById('video')
const serverUrl = 'http://localhost:8000';
const textBox = document.getElementById('log');
const textBox1 = document.getElementById('log1');
const textBox2 = document.getElementById('log2');
const iframe = document.getElementById('iframeid');
        
Promise.all([
  faceapi.nets.tinyFaceDetector.loadFromUri('/static/models'),
  faceapi.nets.faceLandmark68Net.loadFromUri('/static/models'),
  faceapi.nets.faceRecognitionNet.loadFromUri('/static/models'),
  faceapi.nets.faceExpressionNet.loadFromUri('/static/models')
]).then(startVideo)

function startVideo() {
  navigator.getUserMedia(
    { video: {} },
    stream => video.srcObject = stream,
    err => console.error(err)
  )
}

function appendText(text) {
  textBox.innerHTML += text + '<br>';
  textBox.scrollTop = textBox.scrollHeight;
}

video.addEventListener('play', getData);

function getData() {
  const canvas = faceapi.createCanvasFromMedia(video);
  document.body.append(canvas);
  const displaySize = {width: 1, height: 1};//{width: video.width, height: video.height }
  faceapi.matchDimensions(canvas, displaySize);

  const expressionFrequency = new Map(); // Create a hashmap to store expression frequency

  setInterval(async () => {
    const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions()
    const resizedDetections = faceapi.resizeResults(detections, displaySize);
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    // faceapi.draw.drawDetections(canvas, resizedDetections)
    // faceapi.draw.drawFaceLandmarks(canvas, resizedDetections)
    // faceapi.draw.drawFaceExpressions(canvas, resizedDetections)

    // Log the detected expression and update frequency in hashmap
    if (resizedDetections && resizedDetections.length > 0) {
      const expression = resizedDetections[0].expressions.asSortedArray()[0]
      textBox1.innerHTML = 'Detected expression: ' + expression.expression;
      textBox2.innerHTML = 'Number of people: ' + detections.length;
      console.log('Detected expression:', expression.expression)
      console.log('people', detections.length);
      const currentFrequency = expressionFrequency.get(expression.expression) || 0;
      expressionFrequency.set(expression.expression, currentFrequency + 1);
    }
  }, 100)

  // Log the highest frequency expression
  setInterval(() => {
    let highestFrequency = 0;
    let highestExpression = '';
    for (const [expression, frequency] of expressionFrequency) {
      if (frequency > highestFrequency && expression !== 'neutral') {
        highestFrequency = frequency;
        highestExpression = expression;
      }
    }
    const currentTime = new Date().toLocaleTimeString();
    appendText(currentTime + ': ' + highestExpression);
    console.log('Expressions recorded:', expressionFrequency);
    console.log('Highest frequency expression:', highestExpression);

    // Send POST request to /mood endpoint
    fetch(`${serverUrl}/mood?mood=${highestExpression}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      mode: 'no-cors',
    })
      .then(response => {
        iframe.src = iframe.src;
        if (response.ok) {
          return response.json();
        } else {
          throw new Error('POST request failed');
        }
      })
      .then(data => {
        console.log('POST request successful:', data);
      })
      .catch(error => {
        console.error('Error:', error);
      });
      // Reset the frequency hashmap
      expressionFrequency.clear();
    }, 10000);
}
