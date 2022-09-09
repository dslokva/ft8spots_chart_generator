unit Squares;

interface

uses
  Windows, SysUtils, Classes, Math
  ;
  //, Types;

const
  NIL_POINT: TPoint = (X: MAXINT; Y: MAXINT);
  NIL_RECT: TRect = (Left: 0; Top: 0; Right: 0; Bottom: 0);


//P: x = longitude, y = latitude in Units
//1 Unit = 20 arc seconds
//Minus for West and for South

function LatLonToSquare(P: TPoint; Len: integer): AnsiString;
function SquareToLatLon(S: AnsiString): TPoint;
function SquareToLatLonStr(S: AnsiString): string;
function SquareToRect(S: AnsiString): TRect;


implementation

const
  //angles expressed in 20" units
  UinD = 180;                         //20" units in 1 arc degree
  U90 = UinD * 90;                    //units in 180 degrees
  U180 = UinD * 180;                  //units in 180 degrees
  U360 = UinD * 360;                  //units in 360 degrees

  //square sizes
  W2 = U360 div 18;   H2 = U180 div 18;  //18 x 18
  W4 = W2 div 10;     H4 = H2 div 10;     //10 x 10
  W6 = W4 div 24;     H6 = H4 div 24;     //24 x 24

function LatLonToSquare(P: TPoint; Len: integer): AnsiString;
begin
  if P.x < -U180 then Inc(P.x, U360);
  if P.x >= U180 then Dec(P.x, U360);
  
  Result := StringOfChar(' ', Len);

  //field
  Inc(P.x, U180);
  Inc(P.y, U90);
  Result[1] := AnsiChar(Ord('A') + P.x div W2);
  Result[2] := AnsiChar(Ord('A') + P.y div H2);
  if Len < 4 then Exit;

  //square
  P.x := P.x mod W2;
  P.y := P.y mod H2;
  Result[3] := AnsiChar(Ord('0') + P.x div W4);
  Result[4] := AnsiChar(Ord('0') + P.y div H4);
  if Len < 6 then Exit;

  //subsquare
  P.x := P.x mod W4;
  P.y := P.y mod H4;
  Result[5] := AnsiChar(Ord('a') + P.x div W6);
  Result[6] := AnsiChar(Ord('a') + P.y div H6);
end;


function SquareCorner(S: string): TPoint;
begin
  Result := NIL_POINT;
  S := UpperCase(Trim(S));
  if not (Length(S) in [2,4,6]) then begin Result := NIL_POINT; Exit; end;

  //Lat/Lon of the bottom-left corner of the square

  if Length(S) >= 2 then
    begin
    if not ((S[1] in ['A'..'R']) and (S[2] in ['A'..'R']) ) then begin Result := NIL_POINT; Exit; end;
    Result.x := (Ord(S[1]) - Ord('A')) * W2 - U180;
    Result.y := (Ord(S[2]) - Ord('A')) * H2 - U90;
    end;

  if Length(S) >= 4 then
    begin
    if not ((S[3] in ['0'..'9']) and (S[4] in ['0'..'9']) ) then begin Result := NIL_POINT; Exit; end;
    Inc(Result.x, (Ord(S[3]) - Ord('0')) * W4);
    Inc(Result.y, (Ord(S[4]) - Ord('0')) * H4);
    end;

  if Length(S) = 6 then
    begin
    if not ((S[5] in ['A'..'X']) and (S[6] in ['A'..'X']) ) then begin Result := NIL_POINT; Exit; end;
    Inc(Result.x, (Ord(S[5]) - Ord('A')) * W6);
    Inc(Result.y, (Ord(S[6]) - Ord('A')) * H6);
    end;
end;

function SquareToLatLon(S: AnsiString): TPoint;
begin
  Result := SquareCorner(S);
  //from corner to center
  case Length(S) of
    2: begin Inc(Result.x, W2 div 2); Inc(Result.y, H2 div 2); end;
    4: begin Inc(Result.x, W4 div 2); Inc(Result.y, H4 div 2); end;
    6: begin Inc(Result.x, W6 div 2); Inc(Result.y, H6 div 2); end;
  end;
end;


//------------------------------------------------------------------------------
//                                   NEW!
//------------------------------------------------------------------------------
function SquareToLatLonStr(S: AnsiString): string;
const
  LatCh: array[boolean] of string = ('S', 'N');
  LonCh: array[boolean] of string = ('W', 'E');
var
  P: TPoint;
begin
  Result := '';
  if not (Length(S) in [2,4,6]) then Exit;

  S := UpperCase(S);

  //Lat/Lon of the bottom-left corner
  P := POINT(-180 * UinD, -90 * UinD);

  if Length(S) >= 2 then
    begin
    if not ((S[1] in ['A'..'R']) and (S[2] in ['A'..'R']) ) then Exit;
    Inc(P.x, (Ord(S[1]) - Ord('A')) * W2);
    Inc(P.y, ((Ord(S[2]) - Ord('A')) * W2) div 2);
    end;

  if Length(S) >= 4 then
    begin
    if not ((S[3] in ['0'..'9']) and (S[4] in ['0'..'9']) ) then Exit;
    Inc(P.x, (Ord(S[3]) - Ord('0')) * W4);
    Inc(P.y, ((Ord(S[4]) - Ord('0')) * W4) div 2);
    end;

  if Length(S) = 6 then
    begin
    if not ((S[5] in ['A'..'X']) and (S[6] in ['A'..'X']) ) then Exit;
    Inc(P.x, (Ord(S[5]) - Ord('A')) * W6);
    Inc(P.y, ((Ord(S[6]) - Ord('A')) * W6) div 2);
    end;


  //square corner to center
  case Length(S) of
    2: begin Inc(P.x, W2 div 2); Inc(P.y, H2 div 2); end;
    4: begin Inc(P.x, W4 div 2); Inc(P.y, H4 div 2); end;
    6: begin Inc(P.x, W6 div 2); Inc(P.y, H6 div 2); end;
  end;

  Result := Format('%d°%s  %d°%s',
    [Round(Abs(P.y) / UinD), LatCh[P.y >= 0],
     Round(Abs(P.x) / UinD), LonCh[P.x >= 0]]);
end;

function SquareToRect(S: AnsiString): TRect;
var
  P: TPoint;
begin
  P := SquareCorner(S);
  if P.X = MAXINT then begin Result := NIL_RECT; Exit; end;

  Result.Left := P.X;
  Result.Bottom := P.Y;

  case Length(S) of
    2: begin Inc(P.x, W2); Inc(P.y, H2); end;
    4: begin Inc(P.x, W4); Inc(P.y, H4); end;
    6: begin Inc(P.x, W6); Inc(P.y, H6); end;
  end;

  Result.Right := P.X;
  Result.Top := P.Y;
end;


end.
