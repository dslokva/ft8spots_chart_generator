unit Polygn;

interface

uses
  Windows, SysUtils, Classes, PolyOvl, Math;


type
  PPolygon = ^TPolygon;
  TPolygon = record
    Name: string[7];
    R: TRect;
    Points: TPointArray;
  end;

  TPolygonArray = array of TPolygon;


  
  TPolygons = class
   private
    FItems: TPolygonArray;
  public
    procedure LoadFromStream(St: TStream);
    procedure LoadFromFile(AFileName: TFileName);
    function GetItems(AName: string): TPolygonArray;
    property Items: TPolygonArray read FItems;
  end;


function PolygonsOverlap(Pg1, Pg2: PPolygon): boolean;
function BndRect(APoints: TPointArray): TRect;




implementation


function BndRect(APoints: TPointArray): TRect;
var
  i: integer;
begin
  Result.TopLeft := APoints[0];
  Result.BottomRight := APoints[0];
  
  for i:=1 to High(APoints) do
    begin
    Result.Left := Min(Result.Left, APoints[i].x);
    Result.Right := Max(Result.Right, APoints[i].x);
    Result.Top := Min(Result.Top, APoints[i].y);
    Result.Bottom := Max(Result.Bottom, APoints[i].y);
    end;

  Inc(Result.Right);
  Inc(Result.Bottom);
end;





function PolygonsOverlap(Pg1, Pg2: PPolygon): boolean;
begin
  Result := false;

  if (Pg1 = nil) or (Pg2 = nil) then Exit;

  if Pg2.R.Left > Pg1.R.Right then Exit;
  if Pg1.R.Left > Pg2.R.Right then Exit;

  if Pg2.R.Top > Pg1.R.Bottom then Exit;
  if Pg1.R.Top > Pg2.R.Bottom then Exit;

  Result := IsPolygonOverlap(Pg1.Points, Pg2.Points);
end;



{ TPolygons }


function TPolygons.GetItems(AName: string): TPolygonArray;
var
  i: integer;
begin
  Result := nil;
  for i:=0 to High(FItems) do
    if FItems[i].Name = AName then
      begin
      SetLength(Result, Length(Result)+1);
      Result[High(Result)] := FItems[i];
      end;
end;


procedure TPolygons.LoadFromFile(AFileName: TFileName);
var
  Fs: TFileStream;
begin
  Fs := TFileStream.Create(AFileName, fmOpenRead);
  try
    LoadFromStream(Fs);
  finally
    Fs.Free;
  end;
end;

procedure TPolygons.LoadFromStream(St: TStream);
var
  i, Cnt, Len: Int32;
begin
  //number of polygons
  St.ReadBuffer(Cnt, SizeOf(Cnt));
  SetLength(FItems, Cnt);

  for i:=0 to High(FItems) do
    begin
    //polygon name and rect
    St.ReadBuffer(FItems[i], SizeOf(TPolygon)-4);

    //number of points
    Len := Int32(FItems[i].Points);
    Int64(FItems[i].Points) := 0;
    SetLength(FItems[i].Points, Len);

    //point data
    St.ReadBuffer(FItems[i].Points[0], Len * SizeOf(TPoint));
    end;
end;


end.

