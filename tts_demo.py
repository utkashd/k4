from openai import OpenAI

client = OpenAI()

response = client.audio.speech.create(
    model="tts-1",
    voice="onyx",
    input="What's up!? My name is Fred.",
)

response.write_to_file("tmp/speech.mp3")
