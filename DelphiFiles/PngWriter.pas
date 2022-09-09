unit PngWriter;

interface

uses
  SysUtils, Vcl.Graphics, Vcl.Imaging.PngImage, ParamParser, IOUtils;

procedure  SavePng(Bmp: TBitmap; Data: TFt8ChartData);

implementation

procedure  SavePng(Bmp: TBitmap; Data: TFt8ChartData);
var
  FileName: TFileName;
begin
  FileName := Format('%s%d_ITU-%.02d_ITU-%.02d_%dm.png', [
    IncludeTrailingPathDelimiter(Data.output_folder),
    Data.year,
    Data.itu_zone_1,
    Data.itu_zone_2,
    Data.band_meters
  ]);

  with TPngImage.Create do
  try
    Assign(Bmp);
    SaveToFile(FileName);
  finally
    Free;
  end;
end;


end.
