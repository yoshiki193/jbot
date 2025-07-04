import asyncio
import hashlib
import multiprocessing
from pathlib import Path
from voicevox_core.asyncio import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

async def main(text:str, style_id:int) -> str:
    onnxruntime = await Onnxruntime.load_once(filename = f"./onnxruntime/lib/{Onnxruntime.LIB_VERSIONED_FILENAME}")

    synthesizer = Synthesizer(
        onnxruntime,
        await OpenJtalk.new("./dict/open_jtalk_dic_utf_8-1.11"),
        acceleration_mode="AUTO",
        cpu_num_threads=max(
            multiprocessing.cpu_count(), 2
        ),
    )

    async with await VoiceModelFile.open("./models/vvms/0.vvm") as model:
        await synthesizer.load_voice_model(model)

    audio_query = await synthesizer.create_audio_query(text, style_id)
    wav = await synthesizer.synthesis(audio_query, style_id)
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    out = Path(text_hash)
    out.write_bytes(wav)

    return text_hash
