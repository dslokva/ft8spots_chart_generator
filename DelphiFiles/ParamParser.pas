unit ParamParser;

interface

uses
  SysUtils, SuperObject, DateUtils;

type
  TFt8ChartData = class
  public
    year: integer;
    itu_zone_1: integer;
    itu_zone_2: integer;
    band_meters: integer;
    output_folder: TFileName;
    ap: array of integer;
    counts: array of integer;
  end;


function ParseParams(AParams: String): TFt8ChartData;

implementation

function ParseParams(AParams: String): TFt8ChartData;
var
  i, Len: integer;
  Sobj: ISuperObject;
begin
  Result := TFt8ChartData.Create;

  Sobj := SO(AParams);
  Result.year := Sobj.AsObject.I['year'];
  Result.itu_zone_1 := Sobj.AsObject.I['itu_zone_1'];
  Result.itu_zone_2:= Sobj.AsObject.I['itu_zone_2'];
  Result.band_meters:= Sobj.AsObject.I['band_meters'];
  Result.output_folder := Sobj.AsObject.S['output_folder'];

  Len := Sobj.AsObject.O['ap'].AsArray.Length;
  if Len <> DaysInAYear(Result.year) then raise Exception.Create('Wrong array length');
  SetLength(Result.ap, Len);
  for i := 0 to Len-1 do Result.ap[i] := SObj.AsObject.O['ap'].AsArray.I[i];

  Len := Sobj.AsObject.O['counts'].AsArray.Length;
  if Len <> (DaysInAYear(Result.year) * 96) then raise Exception.Create('Wrong array length');
  SetLength(Result.counts, Len);
  for i := 0 to Len-1 do Result.counts[i] := Sobj.AsObject.O['counts'].AsArray.I[i];
end;


end.
