unit ItuZones;

interface

uses
  Windows, SysUtils, Classes, Polygn, PolyOvl;

var
  Baricenters: array of TPoint;

function PointToItuZone(P: TPoint): integer;
procedure LoadBaricenters;


implementation

var
  PgCq, PgItu, PgIota: TPolygons;

function GetModuleName: string;
var
  szFileName: array[0..MAX_PATH] of Char;
begin
  FillChar(szFileName, SizeOf(szFileName), #0);
  GetModuleFileName(hInstance, szFileName, MAX_PATH);
  Result := szFileName;
end;


procedure LoadBaricenters;
var
  FilePath: TFileName;
  Lines, Pieces: TStringList;
  Line: string;
  Zone: integer;
begin
  FormatSettings.DecimalSeparator := '.';
  SetLength(Baricenters, 75);

  Lines := TStringList.Create;
  Pieces := TStringList.Create;

  FilePath := ExtractFilePath(GetModuleName) + 'ItuZoneBaryCenters.csv';
  Lines.LoadFromFile(FilePath);
  Lines.Delete(0);
  for Line in Lines do
    begin
    Pieces.CommaText := Line;
    Zone := StrToInt(Pieces[2]);
    Baricenters[zone].X := Round(StrToFloat(Pieces[0]) * 180);
    Baricenters[zone].Y := Round(StrToFloat(Pieces[1]) * 180);
    end;

  Pieces.Free;
  Lines.Free;
end;


procedure LoadZoneBoundaries;
var
  Dir: TFileName;
  i: integer;
  Fs: TFileStream;
  Names: TStringList;
  Zone: integer;
  FilePath: TFileName;
begin
  PgCq := TPolygons.Create;
  PgItu := TPolygons.Create;
  PgIota := TPolygons.Create;
  FilePath := ExtractFilePath(GetModuleName) + 'Poly.dat';

  Fs := TFileStream.Create(FilePath, fmOpenRead);
  try
    PgCq.LoadFromStream(Fs);
    PgItu.LoadFromStream(Fs);
    PgIota.LoadFromStream(Fs);
  finally
    Fs.Free;
  end;
end;

function PointToItuZone(P: TPoint): integer;
var
  i: integer;
begin
  if PgItu = nil then LoadZoneBoundaries;

  for i:=0 to High(PgItu.Items) do
    if PtInRect(PgItu.Items[i].R, P) and
       IsPointInPolygon(P, PgItu.Items[i].Points)
         then Exit(StrToInt(PgItu.Items[i].Name));
  Result := 0;
end;


end.
