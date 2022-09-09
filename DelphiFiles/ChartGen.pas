unit ChartGen;

interface

uses
  Windows, SysUtils, Vcl.Graphics, Types, DateUtils, ParamParser, Math,
  Classes, MyMath, Schlyter, ItuZones;


function DrawBg(Data: TFt8ChartData): TBitmap;
procedure DrawSunrise(Bmp: TBitmap; Data: TFt8ChartData);
procedure DrawCounts(Bmp: TBitmap; Data: TFt8ChartData);

implementation

const
  MARG = 20;
  AP_HEIGHT = 56;
  LEFT_MARKS = 18;
  BOTTOM_MARKS = 15;
  SLOT_SIZE = 6;
  SlotsY = 24 * 4;


var
  SlotsX: integer;
  DataRect: TRect;

function ISO8601ToDateTime(Value: String):TDateTime;
var
    FormatSettings: TFormatSettings;
begin
    GetLocaleFormatSettings(GetThreadLocale, FormatSettings);
    FormatSettings.DateSeparator := '-';
    FormatSettings.ShortDateFormat := 'yyyy-MM-dd';
    Result := StrToDate(Value, FormatSettings);
end;

function DrawBg(Data: TFt8ChartData): TBitmap;
var
  Bmp: TBitmap;
  R: TRect;
  PixX, PixY, x, y, m, LastX: integer;
  FrameColor, GridColor: TColor;
  DateStr: string;
  MonthStart0, MonthStart, D: TDateTime;
  PixR, PixS: integer;
begin
  FrameColor := clWhite;
  GridColor := clWhite;

  //rects
  SlotsX := DaysInYear(Data.year);
  DataRect := RECT(0, 0, SlotsX * SLOT_SIZE, SlotsY * SLOT_SIZE);
  OffsetRect(DataRect, MARG + LEFT_MARKS, MARG + AP_HEIGHT);
  R := RECT(0, 0, DataRect.Right + LEFT_MARKS + MARG + 1, DataRect.Bottom + BOTTOM_MARKS + MARG + 1);

  //bg
  Bmp := TBitmap.Create();
  Bmp.PixelFormat := pf32bit;
  Bmp.SetSize(R.Right, R.Bottom);
  Bmp.Canvas.Brush.Color := clBlack;
  R := RECT(0,0,Bmp.Width, Bmp.Height);
  Bmp.Canvas.FillRect(R);

  Bmp.Canvas.Pen.Style := psDot;
  Bmp.Canvas.Pen.Color := GridColor;
  Bmp.Canvas.Brush.Style := bsClear;
  Bmp.Canvas.Font.Color := clWhite;

  //two frames
  Bmp.Canvas.Brush.Color := FrameColor;
  R := RECT(DataRect.Left, MARG, DataRect.Right, MARG + AP_HEIGHT-5);
  Bmp.Canvas.FrameRect(R);
  Bmp.Canvas.FrameRect(DataRect);

  //hor grid
  Bmp.Canvas.Brush.Style := bsClear;
  for y:=0 to 6 do
    begin
    PixY := DataRect.Bottom-2 - y * 4*4*SLOT_SIZE + 1;
    if y = 6 then Inc(PixY);

    Bmp.Canvas.MoveTo(DataRect.Left, PixY);
    Bmp.Canvas.LineTo(DataRect.Right, PixY);
    Bmp.Canvas.TextOut(20, PixY-7, Format('%.02d', [y*4]));
    Bmp.Canvas.TextOut(DataRect.Right+10, PixY-7, Format('%.02d', [y*4]));
    end;

  //vert grid
  Bmp.Canvas.Brush.Style := bsClear;
  MonthStart0 := ISO8601ToDateTime(Format('%d-01-01', [Data.year]));
  LastX := DataRect.Left;
  for m:=1 to 12 do
    begin
    DateStr := Format('%d-%.02d-01', [Data.year, m]);
    MonthStart := ISO8601ToDateTime(DateStr);
    PixX := DataRect.Left + Round(MonthStart - MonthStart0)*SLOT_SIZE - 1;

    Bmp.Canvas.Pen.Color := clWhite;
    Bmp.Canvas.MoveTo(PixX, DataRect.Top);
    Bmp.Canvas.LineTo(PixX, DataRect.Bottom);

    Bmp.Canvas.Pen.Color := clGray;
    Bmp.Canvas.MoveTo(PixX, MARG);
    Bmp.Canvas.LineTo(PixX, MARG + AP_HEIGHT - 6);

    DateStr := FormatDateTime('mmm yyyy', MonthStart);
    Bmp.Canvas.TextOut(PixX + 70, DataRect.Bottom + 4, DateStr);
    end;

  //Ap grid
  PixY := MARG + AP_HEIGHT - 6 - 25;
  Bmp.Canvas.Pen.Color := clGray;
  Bmp.Canvas.Brush.Style := bsClear;
  Bmp.Canvas.MoveTo(DataRect.Left, PixY);
  Bmp.Canvas.LineTo(DataRect.Right, PixY);
  Bmp.Canvas.TextOut(15, MARG-7, '100');
  Bmp.Canvas.TextOut(20, MARG-7+25, '50');
  Bmp.Canvas.TextOut(DataRect.Right + 10, MARG-7, '100');
  Bmp.Canvas.TextOut(DataRect.Right + 10, MARG-7+25, '50');

  //Ap
  Bmp.Canvas.Brush.Color := $FFFFA0;
  for x :=0 to SlotsX-1 do
    begin
    PixX := DataRect.Left + x * SLOT_SIZE;
    PixY := MARG + AP_HEIGHT - 6;
    Bmp.Canvas.FillRect(RECT(PixX + 1, PixY - Data.ap[x] div 2 + 1, PixX+4, PixY));
    end;

  //two frames
  Bmp.Canvas.Brush.Color := FrameColor;
  R := RECT(DataRect.Left, MARG, DataRect.Right, MARG + AP_HEIGHT-5);
  Bmp.Canvas.FrameRect(R);
  Bmp.Canvas.FrameRect(DataRect);

  //labels
  Bmp.Canvas.Brush.Style := bsClear;
  Bmp.Canvas.Font.Color := clWhite;
  Bmp.Canvas.TextOut(DataRect.Left + 6, MARG + 3, 'Ap');
  Bmp.Canvas.TextOut(DataRect.Left + 6, DataRect.Top+3, 'UTC');
  Bmp.Canvas.TextOut(DataRect.Right - 27, DataRect.Bottom-16, 'Date');

  Result := Bmp;
end;

procedure DrawCounts(Bmp: TBitmap; Data: TFt8ChartData);
const
  Palette: array[0..9] of TColor = (
    $FF8888, $FFCC88,
    $FFFF88, $CCFF88, $88FF88,
    $88FFCC, $88FFFF, $88CCFF, $CCCCFF, $8888FF);
var
  Utc, Snr, MinUtc, Slot, x, y, Cnt, MaxCount, AvgCount, i, Idx: integer;
  MinSnr, MaxSnr: integer;
  PixX, PixY: integer;
begin
  AvgCount := 0;
  Cnt := 0;
  for i:=0 to High(Data.Counts) do if Data.Counts[i] > 0 then
    begin Inc(AvgCount, Data.Counts[i]); Inc(Cnt); end;
  if Cnt > 0 then AvgCount := AvgCount div Cnt;
  MaxCount := AvgCount * 3;
  for i:=0 to High(Data.Counts) do Data.Counts[i] := Min(MaxCount, Data.Counts[i]);

  Slot := 0;
  for x :=0 to SlotsX-1 do
    for y:=0 to SlotsY-1 do
      begin
      if Data.Counts[Slot] > 0 then
        begin
        Idx := Min(High(Palette), Trunc(Log2(Data.Counts[Slot])));
        Bmp.Canvas.Brush.Color := Palette[Idx];
        PixY := MARG + AP_HEIGHT + (SlotsY-1-y) * SLOT_SIZE;
        PixX := DataRect.Left + x * SLOT_SIZE;
        Bmp.Canvas.FillRect(RECT(PixX+1,PixY+1, PixX+4, PixY+4));
        end;
      Inc(Slot);
      end;
end;


procedure DrawSunrise(Bmp: TBitmap; Data: TFt8ChartData);
var
  Sun: TSchlyterSun;
  PixX, PixY, x: integer;
  PixR, PixS: integer;
  P1, P2: TPoint;
  D: TDateTime;
begin
  SlotsX := DaysInYear(Data.year);

  if Baricenters = nil then LoadBaricenters;
  P1 := Baricenters[Data.itu_zone_1];
  P2 := Baricenters[Data.itu_zone_2];

  Bmp.Canvas.Brush.Color := clYellow;
  Sun := TSchlyterSun.Create;
  try
    Sun.Observer := GPOINT(P1);
    D := ISO8601ToDateTime(Format('%d-01-01', [Data.year]));
    for x:=0 to SlotsX-1 do
      begin
      Sun.Utc := D + x;
      PixX := DataRect.Left + x * SLOT_SIZE;
      PixR := DataRect.Bottom - Round(Frac(Sun.Sunrise) * 24 * 4 * SLOT_SIZE);
      PixS := DataRect.Bottom - Round(Frac(Sun.Sunset) * 24 * 4 * SLOT_SIZE);
      if Odd(x) then Bmp.Canvas.FillRect(RECT(PixX, PixS, PixX+SLOT_SIZE, PixS+1));
      Bmp.Canvas.FillRect(RECT(PixX, PixR, PixX+SLOT_SIZE, PixR+1));
      end;

    Bmp.Canvas.Brush.Color := clRed;
    Sun.Observer := GPOINT(P2);
    for x:=0 to SlotsX-1 do
      begin
      Sun.Utc := D + x;
      PixX := DataRect.Left + x * SLOT_SIZE;
      PixR := DataRect.Bottom - Round(Frac(Sun.Sunrise) * 24 * 4 * SLOT_SIZE);
      PixS := DataRect.Bottom - Round(Frac(Sun.Sunset) * 24 * 4 * SLOT_SIZE);
      if Odd(x) then Bmp.Canvas.FillRect(RECT(PixX, PixS, PixX+SLOT_SIZE, PixS+1));
      Bmp.Canvas.FillRect(RECT(PixX, PixR, PixX+SLOT_SIZE, PixR+1));
      end;
  finally
    Sun.Free;
  end;
  end;


end.
