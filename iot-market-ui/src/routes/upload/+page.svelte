<script lang="ts">
  let files: FileList | null = null;
  let framesDir = '';
  let outputDir = '';
  let status = '';
  let output = '';

  let eventSource: EventSource | null = null;

  // Upload image files
  async function handleUpload() {
    if (!files) {
      status = 'Please select an image file first';
      return;
    }
    status = 'Uploading pictures...';
    output = '';
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('frames', files[i]);
    }
    const res = await fetch('http://127.0.0.1:5005/api/upload_frames', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    status = data.status === 'success' ? 'Image uploaded successfully!' : 'Image upload failed';
    output = JSON.stringify(data.files, null, 2);
  }

  // Generate animation and stream logs in real time
  async function handleSubmit() {
    status = 'Processing...';
    output = '';
    await fetch('http://127.0.0.1:5005/api/generate_movie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frames_dir: framesDir, output_dir: outputDir })
    });
    if (eventSource) eventSource.close();
    eventSource = new EventSource('http://127.0.0.1:5005/api/generate_movie/log');
    eventSource.onmessage = (event) => {
      output += event.data + '\n';
    };
  }
</script>

<style>
  .center-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  h2, form, div, p, pre {
    text-align: center;
  }
  form, div {
    width: 100%;
    max-width: 500px;
    margin: 0 auto;
  }
  .section-gap {
    margin-top: 32px;
    margin-bottom: 16px;
  }
</style>

<div class="center-container">
  <h2>Upload data and generate animation</h2>

  <!-- File upload section -->
  <div>
    <label>
      Select image files (multiple selections possible):
      <input type="file" multiple bind:files={files} />
    </label>
    <button type="button" on:click={handleUpload}>Upload pictures</button>
  </div>

  <hr class="section-gap" style="width: 80%;" />

  <!-- Directory inputs and generate animation section -->
  <form class="section-gap" on:submit|preventDefault={handleSubmit}>
    <label>
      Original image directory（frames_dir）:
      <input bind:value={framesDir} required />
    </label>
    <br />
    <label>
      Output Directory（output_dir）:
      <input bind:value={outputDir} required />
    </label>
    <br />
    <button type="submit">Generate Animation</button>
  </form>

  <p>{status}</p>
  <pre>{output}</pre>
</div>