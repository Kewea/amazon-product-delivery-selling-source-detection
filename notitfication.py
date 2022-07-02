import platform
import subprocess


def send_mac_notification(title: str, message: str) -> None:
    """
    Send message to mac notification center

    :param title:
    :param message:
    :return:
    """
    cmd = '''
    on run argv
      display notification (item 2 of argv) with title (item 1 of argv)
    end run
    '''
    if platform.system() == "Darwin":
        subprocess.call(['osascript', '-e', cmd, title, message])
