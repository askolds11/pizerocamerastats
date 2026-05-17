WITH filtered_pictures AS (
    SELECT
        cp."PictureRequestId",
        cp."CameraId",
        cp."NtpErrorMillis",
        cp."FrameDuration" AS "CameraFrameDurationUs",
        cp."ExposureTime" AS "ExposureTimeUs",
        cp."PictureTaken" - (COALESCE(cp."ExposureTime", 0) * INTERVAL '1 microsecond') AS "AdjustedPictureTaken"
    FROM "CameraPictures" cp
             JOIN "PictureRequests" pr
                  ON cp."PictureRequestId" = pr."Uuid"
    WHERE cp."CameraPictureStatus" IS NOT NULL
      AND cp."PictureTaken" IS NOT NULL
      AND cp."Synced" = TRUE
),
     request_stats AS (
         SELECT
             fp."PictureRequestId",
             MIN(fp."AdjustedPictureTaken") AS "MinAdjustedPictureTaken",
             MAX(CASE WHEN fp."CameraId" = 'A1' THEN fp."AdjustedPictureTaken" END) AS "A1AdjustedPictureTaken",
             MAX(CASE WHEN fp."CameraId" = 'A1' THEN fp."NtpErrorMillis" END) AS "A1NtpErrorMillis",
             MAX(CASE WHEN fp."CameraId" = 'A1' THEN fp."CameraFrameDurationUs" END) AS "A1FrameDurationUs"
         FROM filtered_pictures fp
         GROUP BY fp."PictureRequestId"
     ),
     request_base AS (
         SELECT
             rs."PictureRequestId",
             rs."A1FrameDurationUs",
             CASE
                 WHEN rs."A1AdjustedPictureTaken" IS NOT NULL
                     AND rs."A1FrameDurationUs" IS NOT NULL
                     AND rs."A1FrameDurationUs" <> 0
                     THEN
                     rs."A1AdjustedPictureTaken"
                         - (
                               TRUNC(
                                       (EXTRACT(EPOCH FROM (rs."A1AdjustedPictureTaken" - rs."MinAdjustedPictureTaken")) * 1000000.0)
                                           / rs."A1FrameDurationUs"
                               )::bigint
                                   * rs."A1FrameDurationUs"
                               ) * INTERVAL '1 microsecond'
                 WHEN rs."A1AdjustedPictureTaken" IS NOT NULL
                     THEN rs."A1AdjustedPictureTaken"
                 ELSE rs."MinAdjustedPictureTaken"
                 END AS "BaseAdjustedPictureTaken",
             rs."A1NtpErrorMillis" AS "BaseNtpErrorMillis"
         FROM request_stats rs
     )
SELECT
    fp."AdjustedPictureTaken" AS "PictureTaken",
    EXTRACT(EPOCH FROM (fp."AdjustedPictureTaken" - rb."BaseAdjustedPictureTaken")) * 1000 AS "DifferenceMs",
    fp."NtpErrorMillis",
    rb."BaseNtpErrorMillis"
FROM filtered_pictures fp
         JOIN request_base rb
              ON rb."PictureRequestId" = fp."PictureRequestId"
WHERE fp."CameraId" <> 'A1'
ORDER BY "DifferenceMs" DESC;