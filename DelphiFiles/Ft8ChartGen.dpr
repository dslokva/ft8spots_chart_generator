library Ft8ChartGen;

uses
  Windows,
  System.SysUtils,
  System.Classes,
  Vcl.Graphics,
  ParamParser in 'ParamParser.pas',
  ChartGen in 'ChartGen.pas',
  PngWriter in 'PngWriter.pas',
  superobject in 'superobject.pas',
  ItuZones in 'ItuZones.pas',
  Polygn in 'Polygn.pas',
  PolyOvl in 'PolyOvl.pas',
  Squares in 'Squares.pas',
  Schlyter in 'Schlyter.pas',
  MyMath in 'MyMath.pas';

{$R *.res}


//example AParams
//  {
//  "year": 2019,
//  "itu_zone_1": 4,
//  "itu_zone_2": 30,
//  "band_meters": 160,
//  "output_folder": "c:\Images"
//  "ap": [1,5,12,3, ...], // 365/366 Ap values for the year
//  "counts": [1,5,12,3, ...], // (365/366)*24*4 spot counts, one for each 15-min. slot
//  }



function GenerateChart(AParams: PChar): integer; stdcall;
var
  Data: TFt8ChartData;
  Bmp: TBitmap;
begin
  try
    try
      Result := 1;
      Data := ParseParams(AParams);
      Result := 2;
      Bmp := DrawBg(Data);
      Result := 3;
      DrawSunrise(Bmp, Data);
      Result := 4;
      DrawCounts(Bmp, Data);
      Result := 5;
      SavePng(Bmp, Data);
    except
      Exit(Result);
    end;
  finally
    Bmp.Free;
    Data.Free;
  end;

  Result := 0;
end;

function SquareToItuZone(ASquare: PChar): integer; stdcall;
begin
  Result := PointToItuZone(SquareTolatLon(ASquare));
end;





exports GenerateChart, SquareToItuZone;

begin
end.
