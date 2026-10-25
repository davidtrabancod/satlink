# Run with PowerShell 7 (pwsh) so accented text is read as UTF-8.
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
$outputDirectory = Join-Path $PSScriptRoot '..\public'

function New-Canvas([int]$width, [int]$height) {
    $bitmap = [System.Drawing.Bitmap]::new($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    return @{ Bitmap = $bitmap; Graphics = $graphics }
}

function Draw-Orbit($graphics, [float]$x, [float]$y, [float]$size, [float]$lineWidth) {
    $orbitColor = [System.Drawing.Color]::FromArgb(175, 129, 228, 237)
    $pen = [System.Drawing.Pen]::new($orbitColor, $lineWidth)
    $graphics.DrawEllipse($pen, $x, $y, $size, $size)
    $graphics.TranslateTransform($x + $size / 2, $y + $size / 2)
    $graphics.RotateTransform(-36)
    $graphics.DrawEllipse($pen, -$size * .55, -$size * .2, $size * 1.1, $size * .4)
    $graphics.ResetTransform()
    $pen.Dispose()
    $dot = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#D7FF8A'))
    $graphics.FillEllipse($dot, $x + $size * .77, $y + $size * .1, $size * .095, $size * .095)
    $dot.Dispose()
}

$icon = New-Canvas 64 64
$iconBackground = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#0C1B2B'))
$icon.Graphics.FillRectangle($iconBackground, 0, 0, 64, 64)
Draw-Orbit $icon.Graphics 8 8 48 2.2
$icon.Bitmap.Save((Join-Path $outputDirectory 'favicon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$iconBackground.Dispose(); $icon.Graphics.Dispose(); $icon.Bitmap.Dispose()

$card = New-Canvas 1200 630
$rect = [System.Drawing.Rectangle]::new(0, 0, 1200, 630)
$gradient = [System.Drawing.Drawing2D.LinearGradientBrush]::new($rect, [System.Drawing.ColorTranslator]::FromHtml('#081120'), [System.Drawing.ColorTranslator]::FromHtml('#12344B'), 0)
$card.Graphics.FillRectangle($gradient, $rect)
$gradient.Dispose()
$gridPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(15, 130, 205, 230), 1)
for ($x = 0; $x -le 1200; $x += 76) { $card.Graphics.DrawLine($gridPen, $x, 0, $x, 630) }
for ($y = 0; $y -le 630; $y += 76) { $card.Graphics.DrawLine($gridPen, 0, $y, 1200, $y) }
$gridPen.Dispose()
$accentPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(90, 134, 222, 235), 1)
$card.Graphics.DrawLine($accentPen, 75, 112, 1125, 112)
$card.Graphics.DrawLine($accentPen, 75, 530, 1125, 530)
$accentPen.Dispose()
Draw-Orbit $card.Graphics 770 150 320 3
$brandBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#D7FF8A'))
$mainBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#F3F9FF'))
$subBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#A9D8EE'))
$brandFont = [System.Drawing.Font]::new('Segoe UI', 22, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$titleFont = [System.Drawing.Font]::new('Segoe UI', 61, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$subFont = [System.Drawing.Font]::new('Segoe UI', 27, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$smallFont = [System.Drawing.Font]::new('Consolas', 17, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$card.Graphics.DrawString('SATLINK STUDIO', $brandFont, $brandBrush, 78, 70)
$card.Graphics.DrawString('El cielo, en movimiento.', $titleFont, $mainBrush, 72, 229)
$card.Graphics.DrawString('Radar de satélites en directo', $subFont, $subBrush, 79, 326)
$card.Graphics.DrawString('ISS · STARLINK · PASES · ÓRBITAS', $smallFont, $subBrush, 81, 481)
$card.Bitmap.Save((Join-Path $outputDirectory 'og-satlink.png'), [System.Drawing.Imaging.ImageFormat]::Png)
foreach ($item in @($brandBrush, $mainBrush, $subBrush, $brandFont, $titleFont, $subFont, $smallFont)) { $item.Dispose() }
$card.Graphics.Dispose(); $card.Bitmap.Dispose()
Write-Output 'Generated favicon.png and og-satlink.png.'
