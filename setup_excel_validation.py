#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task_Master.xlsxに入力規則を設定するスクリプト
"""
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from pathlib import Path

def setup_data_validation(file_path: Path):
    """Task_Master.xlsxに入力規則を設定"""
    if not file_path.exists():
        print(f"ファイルが見つかりません: {file_path}")
        return False
    
    wb = openpyxl.load_workbook(file_path)
    ws = wb["TaskList"]
    
    # ヘッダー行を確認して列を特定
    headers = {cell.value: cell.column_letter for cell in ws[1]}
    print(f"{file_path.name}: ヘッダー = {list(headers.keys())}")
    
    # 完了後動作列を特定
    action_col = headers.get("完了後動作") or headers.get("ActionAfter")
    if action_col:
        # 新しい入力規則を作成 (完了後動作)
        dv_action = DataValidation(
            type="list",
            formula1='"None,Pause,Save"',
            allow_blank=True,
            showDropDown=False
        )
        dv_action.error = "無効な値です。None, Pause, Save から選択してください。"
        dv_action.errorTitle = "入力エラー"
        dv_action.prompt = "None（何もしない）、Pause（手動確認）、Save（自動保存）から選択"
        dv_action.promptTitle = "完了後動作"
        
        # 2行目から100行目まで適用
        dv_action.add(f"{action_col}2:{action_col}100")
        ws.add_data_validation(dv_action)
        print(f"  完了後動作列({action_col})に入力規則を設定しました")
    else:
        print(f"  完了後動作列が見つかりません")
    
    # Boolean列にも入力規則を設定 (TRUE/FALSE)
    bool_cols = ["有効", "DLスキップ", "終了後閉じる", "祝日スキップ"]
    for col_name in bool_cols:
        col = headers.get(col_name)
        if col:
            dv_bool = DataValidation(
                type="list",
                formula1='"TRUE,FALSE"',
                allow_blank=True,
                showDropDown=False
            )
            dv_bool.add(f"{col}2:{col}100")
            ws.add_data_validation(dv_bool)
            print(f"  {col_name}列({col})にTRUE/FALSEリストを設定しました")
    
    wb.save(file_path)
    print(f"  保存しました: {file_path.name}")
    return True


if __name__ == "__main__":
    # 両方のTask_Master.xlsxに設定
    base_path = Path(__file__).parent
    files = [
        base_path / "settings" / "production" / "Task_Master.xlsx",
        base_path / "settings" / "test" / "Task_Master.xlsx"
    ]
    
    for file_path in files:
        print(f"\n処理中: {file_path}")
        setup_data_validation(file_path)
    
    print("\n完了!")
