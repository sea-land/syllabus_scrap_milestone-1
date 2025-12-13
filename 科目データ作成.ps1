# ===============================
# 実行ディレクトリを基準にする
# ===============================
Set-Location -Path $PSScriptRoot

# ===============================
# 出力フォルダ作成
# ===============================
$outDir = Join-Path $PSScriptRoot '科目データ'
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

# ===============================
# 出力ヘッダ
# ===============================
$SUBJECT_DATA_HEADER = @(
    '科目ID','学部','科目名','教員名',
    '学期','曜日時限','曜日','時限'
)

# ===============================
# 曜日・時限分解関数
# ===============================
function Split-ClssDate {
    param (
        [Parameter(Mandatory)]
        [string]$Timetable
    )

    $week   = $Timetable.Substring(0,1)
    $period = $Timetable.Substring(1,1)

    return [pscustomobject]@{
        Timetable = $Timetable
        Week      = $week
        Period    = $period
    }
}

# ===============================
# CSV 処理
# ===============================
Get-ChildItem -Path $PSScriptRoot -Filter '*.csv' | ForEach-Object {

    Write-Host "処理中: $($_.Name)"

    $rows = Import-Csv -Path $_.FullName -Encoding UTF8
    $result = @()

    foreach ($row in $rows) {

        $tt = $row.'曜日時限'
        if ([string]::IsNullOrWhiteSpace($tt)) {
            continue
        }

        $baseId = $row.'科目ID'
        $index  = 1

        if ($tt -like '*:*') {
            $parts = $tt -split ':'

            foreach ($p in $parts[1..($parts.Length-1)]) {

                $d = Split-ClssDate $p
                $newId = "$baseId-$index"

                $result += [pscustomobject]@{
                    '科目ID'   = $newId
                    '学部'     = $row.'学部'
                    '科目名'   = $row.'科目名'
                    '教員名'   = $row.'教員名'
                    '学期'     = $row.'学期'
                    '曜日時限' = $d.Timetable
                    '曜日'     = $d.Week
                    '時限'     = $d.Period
                }

                $index++
            }
        }
        else {
            $d = Split-ClssDate $tt

            $result += [pscustomobject]@{
                '科目ID'   = $baseId
                '学部'     = $row.'学部'
                '科目名'   = $row.'科目名'
                '教員名'   = $row.'教員名'
                '学期'     = $row.'学期'
                '曜日時限' = $d.Timetable
                '曜日'     = $d.Week
                '時限'     = $d.Period
            }
        }
    }
    $outDir  = Join-Path $PSScriptRoot '科目データ'
    $outFile = $_.Name -replace '科目ノート', '科目データ'
    $outPath = Join-Path $outDir $outFile
    $result | Export-Csv -Path $outPath -Encoding UTF8 -NoTypeInformation
}

Write-Host "`n全ての処理が完了しました。"
