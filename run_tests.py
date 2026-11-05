import os
import subprocess
import sys

import yaml


def run_com(cmd:str) -> tuple[bool, str, str]:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def run_test(test_file) -> bool:
    with open(test_file, encoding="utf-8") as f:
        test = yaml.safe_load(f)
    name = test["name"]
    print(f" Тест: {name}")
    print(f" Описание: {test.get('description', 'нет описания')}")
    source_file = f"golden_tests/{name}.kot"
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(test["source_code"])
    schedule_file = f"golden_tests/{name}.schedule"
    with open(schedule_file, "w", encoding="utf-8") as f:
        for tick, value in test.get("input_schedule", []):
            f.write(f"{tick} {value}\n")
    ok, out, err = run_com(f"python3 translator.py {source_file}")
    if not ok:
        print(f"ошибка в трансляторе:\n{err}")
        return False
    ok, out, err = run_com("python3 assembler.py program.asm")
    if not ok:
        print(f"ошибка в превращении ассемблера в машинный код:\n{err}")
        return False
    ok, out, err = run_com(f"python3 simulator.py program.bin {schedule_file}")
    if not ok:
        print(f"ошибка в симуляторе:\n{err}")
        return False

    actual_codes = None
    actual_cycles = None
    for line in out.split("\n"):
        if "Вывод (коды байтов):" in line:
            codes_str = line.split(":")[1].strip()
            if codes_str == "[]":
                actual_codes = []
            else:
                actual_codes = [int(x.strip()) for x in codes_str.strip("[]").split(",")]
        if "Всего тактов:" in line:
            actual_cycles = int(line.split(":")[1].strip())
    expected_codes = test.get("output_codes", [])
    expected_cycles = test.get("cycles_total")
    success = True
    if actual_codes == expected_codes:
        print(f"Вывод совпадает: {actual_codes}")
    else:
        print("Вывод НЕ совпадает")
        print(f"Ожидалось: {expected_codes}")
        print(f"Получено:  {actual_codes}")
        success = False
    if expected_cycles and actual_cycles:
        diff = abs(actual_cycles - expected_cycles)
        if diff <= expected_cycles * 0.1:
            print(f"  Такты в пределах нормы: {actual_cycles} (ожидалось примерно {expected_cycles})")
        else:
            print(f"  Такты сильно отличаются: {actual_cycles} / {expected_cycles}")
    return success

def main():
    if not os.path.exists("golden_tests"):
        print("Папка golden_tests не найдена")
        sys.exit(1)
    test_files = [f for f in os.listdir("golden_tests") if f.endswith(".yaml")]
    if not test_files:
        print("Нет тестов в golden_tests")
        sys.exit(1)
    print(f"Найдено тестов: {len(test_files)}")
    results = {}
    for _test in test_files:
        path = os.path.join("golden_tests", _test)
        results[_test] = run_test(path)
    print("В итоге: ")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for _test, success in results.items():
        if success:
            print("Победа, всё получилось")
        else:
            print("Ничего не получилось(((")
    print(f"\nПройдено: {passed}/{total}")
    if passed == total:
        print("Все тесты пройдены")
        sys.exit(0)
    else:
        print("Есть плохие тесты")
        sys.exit(1)

if __name__ == "__main__":
    main()
