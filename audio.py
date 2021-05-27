from pynput import keyboard
import wave, pyaudio, time


paused = False  # global to track if the audio is paused

def audio_stream():

    def on_press(key):
        global paused
        print(key)
        if key == keyboard.Key.space:
            if stream.is_stopped():  # time to play audio
                print('play pressed')
                stream.start_stream()
                paused = False
                return False
            elif stream.is_active():  # time to pause audio
                print('pause pressed')
                stream.stop_stream()
                paused = True
                return False
        return False


    CHUNK = 1024
    wf = wave.open("temp.wav", 'rb')
    p = pyaudio.PyAudio()

    # define callback
    def callback(in_data, frame_count, time_info, status):
        data = wf.readframes(frame_count)
        return (data, pyaudio.paContinue)

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    input=True, output=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

    stream.start_stream()
    while stream.is_active() or paused == True:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
        time.sleep(0.1)

    # stop stream
    stream.stop_stream()
    stream.close()
    wf.close()

    # close PyAudio
    p.terminate()

audio_stream()