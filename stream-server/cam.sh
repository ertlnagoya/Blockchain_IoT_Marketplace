#!/bin/bash
stream_server='localhost'
mediator='../mediator-owner/raw_data'
upload_loc=$(curl http://$stream_server:5024/register)
rm $mediator/link.html
echo "<!doctype html>
<script>
  window.location.replace('rtmp://$stream_server:1935/live/$upload_loc')
</script>" > $mediator/link.html
ffmpeg -f v4l2 -framerate 20 -video_size 800x600 -i /dev/video0 -c:v h264_v4l2m2m -an -f flv rtmp://$stream_server:1935/live/$upload_loc
