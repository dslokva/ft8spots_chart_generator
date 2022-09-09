unit ItuZones;

interface

uses
  Windows, SysUtils, Classes, Polygn, PolyOvl, Generics.Collections;

var
  Baricenters: array of TPoint;

function PointToItuZone(P: TPoint; GridSquareSize: integer): integer;
procedure LoadBaricenters;


implementation

var
  PgCq, PgItu, PgIota: TPolygons;
  FoundZones: TList<integer>;

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

// example R = (left:28800, top:9000, right:32401, bottom:10801)
function RectsOverlap(const R1, R2: TRect): boolean;
begin
  Result := (R2.Left <= R1.Right) and
            (R2.Right >= R1.Left) and
            (R2.Bottom >= R1.Top) and
            (R2.Top <= R1.Bottom);
end;

function RectToPoly(R: TRect): TPointArray;
begin
  SetLength(Result, 5);
  Result[0] := R.TopLeft;
  Result[1] := R.TopLeft; Result[1].X := R.Right;
  Result[2] := R.BottomRight;
  Result[3] := R.BottomRight; Result[3].X := R.Left;
  Result[4] := R.TopLeft;
end;

function PointToItuZone(P: TPoint; GridSquareSize: integer): integer;
var
  i: integer;
  SquarePoly: TPointArray;
  R: TRect;
begin
  if PgItu = nil then LoadZoneBoundaries;

  //  square center in the zone poly

  for i:=0 to High(PgItu.Items) do
    if PtInRect(PgItu.Items[i].R, P) and IsPointInPolygon(P, PgItu.Items[i].Points)
      then Exit(StrToInt(PgItu.Items[i].Name));

  // square rect and zone poly intersect

  if FoundZones = nil
    then FoundZones := TList<integer>.Create
    else FoundZones.Clear;

  case GridSquareSize of
    2: R := RECT(-1800, -900, 1800, 900);
    4: R := RECT(-180, -90, 180, 90);
    6: R := RECT(-8, -4, 8, 4);
    else Exit(0);
  end;
  OffsetRect(R, P.X, P.Y);
  SquarePoly := RectToPoly(R);

  for i:=0 to High(PgItu.Items) do
    if RectsOverlap(PgItu.Items[i].R, R) and IsPolygonOverlap(PgItu.Items[i].Points, SquarePoly)
       then FoundZones.Add(i);

  if FoundZones.Count = 1 then Exit(FoundZones[0]);

  Result := 0;
end;


end.
