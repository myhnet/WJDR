import argparse
from TaskManagerGUI import TaskManagerGUI


def main():
    parser = argparse.ArgumentParser(description='MumuAutomation')
    parser.add_argument('deviceid', type=int, help='Mumu模拟器的编号')
    args = parser.parse_args()

    app = TaskManagerGUI(args.deviceid, r'E:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe')

    try:
        app.run()
    except KeyboardInterrupt:
        print("正在关闭任务管理器...")
        app.root.destroy()


if __name__ == "__main__":
    main()
