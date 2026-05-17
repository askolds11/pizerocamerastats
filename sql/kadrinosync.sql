WITH filtered_pictures AS (SELECT cp."PictureRequestId",
                                  cp."PictureTaken" - (COALESCE(cp."ExposureTime", 0) * INTERVAL '1 microsecond') AS "AdjustedPictureTaken",
                                  cp."NtpErrorMillis",
                                  cp."CameraId"
                           FROM "CameraPictures" cp
                                    JOIN "PictureRequests" pr ON cp."PictureRequestId" = pr."Uuid"
                           WHERE cp."CameraPictureStatus" IS NOT NULL
                             AND cp."PictureTaken" IS NOT NULL
                             AND cp."Synced" = FALSE),
     ranked AS (SELECT fp.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY fp."PictureRequestId"
                           ORDER BY fp."AdjustedPictureTaken" ASC, fp."CameraId" ASC
                           ) AS rn
                FROM filtered_pictures fp),
     request_base AS (SELECT r."PictureRequestId",
                             r."AdjustedPictureTaken"   AS "BasePictureTaken",
                             r."NtpErrorMillis" AS "BaseNtpErrorMillis",
                             r."CameraId"       AS "BaseCameraId"
                      FROM ranked r
                      WHERE r.rn = 1)
SELECT r."AdjustedPictureTaken",
       EXTRACT(EPOCH FROM (r."AdjustedPictureTaken" - rb."BasePictureTaken")) * 1000 AS "DifferenceMs",
       r."NtpErrorMillis",
       rb."BaseNtpErrorMillis"
FROM ranked r
         JOIN request_base rb
              ON rb."PictureRequestId" = r."PictureRequestId"
WHERE r.rn > 1
ORDER BY "DifferenceMs" DESC;