import requests
import colour
import time
import json
import os
import signal
from contextlib import contextmanager

import speech_recognition as sr


class GoveeVoiceControl:

    def __init__(self):
        self.available_colours = [c[0] for c in colour.RGB_TO_COLOR_NAMES.values()]
        self.api_url = "https://developer-api.govee.com/v1/devices/control"
        self.recognise_language = "en-GB"
        self.device = {
            "device": "40:2B:A4:C1:38:39:D1:18",
            "model": "H6159"
        }
        self.http_session = requests.session()
        self.http_session.headers = {
            "Content-Type": "application/json", 
            "Govee-API-Key": os.environ["GOVEE_API_KEY"]
        }
        self.recogniser = sr.Recognizer()
        self.mic = sr.Microphone()

    def __call__(self):
        while True:
            audio = self.listen()
            if not audio:
                continue

            text = self.recognise_audio(audio)
            if not text:
                continue

            self.action(text)

    def __repr__(self):
        return (
            "<GoveeVoiceControl "
            f"device={self.device['device']}"
            f"model={self.device['model']}>"
        )

    def listen(self):
        with self.mic as source:
            try:
                print("Recording...", end="")
                audio = self.recogniser.listen(
                    source, 
                    timeout=5,
                    phrase_time_limit=5
                )
                print("Done")
            except sr.WaitTimeoutError:
                print("No phrase detected")
                audio = None
            finally:
                return audio

    def recognise_audio(self, audio):
        print("Recognising..", end="")
        try:
            # Setting a time limit since this can carry on for ages
            # and it does not seem to provide a request timeout parameter
            with self._time_limit(5):
                text = self.recogniser.recognize_google(
                    audio, 
                    language="en-UK"
                ).lower()
        except sr.UnknownValueError:
            print("Unknown value")
            text = None
        except TimeoutError:
            print("Request timed out")
            text = None
        finally:
            if text:
                print(f"Recognised: {text}")
            return text

    def action(self, text):
        if "lights on" in text:
            self.turn_lights("on")
        elif "lights off" in text:
            self.turn_lights("off")
        elif "colour" in text:
            words_list = text.split()
            try:
                # Get the next word after "colour".
                # This also may fail in the rare case of Google API returning
                # "color" instead (even though the language is set to en-GB??)
                colour_detected = words_list[
                    words_list.index("colour") + 1
                ].capitalize() # <-- colours in colour module are capitalised
            except IndexError:
                print(f"No colour specified/Nothing came after 'colour'")
                return
            
            # Check if the word that came after "colour" is a valid colour
            if colour_detected in self.available_colours:
                self.switch_to_colour(colour_detected)
            else:
                print(f"Colour {colour_detected} is not available")

    @contextmanager
    def _time_limit(self, seconds):
        def _signal_handler(signum, frame):
            raise TimeoutError()
        signal.signal(signal.SIGALRM, _signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            
    def switch_to_colour(self, c):
        colour_obj = colour.Color(c)
        resp = self.http_session.put(
            self.api_url,
            data=json.dumps({
                **self.device,
                "cmd": {
                    "name": "color",
                    "value": {
                        "r": colour_obj.red * 255,
                        "g": colour_obj.green * 255,
                        "b": colour_obj.blue * 255
                    }
                }
            })
        )
        if not resp.ok:
            print(f"Failed to switch colour to '{c}' - {resp.status_code}")

    def turn_lights(self, state):
        resp = self.http_session.put(
            self.api_url,
            data=json.dumps({
                **self.device,
                "cmd": {
                    "name": "turn",
                    "value": state
                }
            })
        )
        if not resp.ok:
            print(f"Failed to turn the lights {state} - {resp.status_code}")




if __name__ == "__main__":
    voice_controller = GoveeVoiceControl()

    # just playing around with dunder/magic methods
    # i know this isn't necessary
    voice_controller()
