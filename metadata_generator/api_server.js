// filepath: metadata_generator/api_server.js
const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const SSE = require('express-sse');
const app = express();
const sse = new SSE();
const multer = require('multer');
const upload = multer({ dest: 'uploads/' }); // Upload to local 'uploads/' directory

app.post('/api/upload_frames', upload.array('frames'), (req, res) => {
  // req.files is the array of uploaded images
  // move these images to frames_dir and then invoke movie_generator.py
  res.json({ status: 'success', files: req.files });
});
app.use(express.json());
app.use(cors());

app.get('/api/generate_movie/log', sse.init);

app.post('/api/generate_movie', (req, res) => {
  const { frames_dir, output_dir } = req.body;
  const py = spawn('python3', ['movie_generator.py', '--frames_dir', frames_dir, '--output_dir', output_dir], { cwd: __dirname });

  py.stdout.on('data', (data) => {
    sse.send(data.toString());
  });
  py.stderr.on('data', (data) => {
    sse.send(data.toString());
  });
  py.on('close', (code) => {
    sse.send(`Process exited with code ${code}`);
  });

  res.json({ status: 'started' });
});

app.listen(5005, () => {
  console.log('API server running at http://127.0.0.1:5005');
});