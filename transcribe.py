import os
import replicate

def transcribe_audio(audio_file):
    # Ensure the file exists
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"The file {output_file_path} does not exist.")

    # Open the file in binary mode
    with open(audio_file, "rb") as file_input:
        input = { "audio": file_input }

        #model_id = "vaibhavs10/incredibly-fast-whisper:3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c"
        #model_id = "turian/insanely-fast-whisper-with-video:4f41e90243af171da918f04da3e526b2c247065583ea9b757f2071f573965408" ##slow!!
        model_id = "openai/whisper:cdd97b257f93cb89dede1c7584e3f3dfc969571b357dbcee08e793740bedd854"
        output = replicate.run(model_id, input=input)
        # Extract the transcription
        transcription = output.get('transcription', 'No transcription found.')
        return transcription