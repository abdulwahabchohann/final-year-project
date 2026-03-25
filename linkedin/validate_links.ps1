param(
    [Parameter(Mandatory = $true)]
    [string]$DemoUrl,
    [string]$GitHubUrl = "https://github.com/abdulwahabchohann/final-year-project"
)

function Test-Url {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $head = Invoke-WebRequest -Uri $Url -Method Head -MaximumRedirection 5 -TimeoutSec 20
        return [pscustomobject]@{
            Url = $Url
            Status = "OK"
            StatusCode = $head.StatusCode
            FinalUrl = $head.BaseResponse.ResponseUri.AbsoluteUri
        }
    } catch {
        try {
            $get = Invoke-WebRequest -Uri $Url -Method Get -MaximumRedirection 5 -TimeoutSec 20
            return [pscustomobject]@{
                Url = $Url
                Status = "OK"
                StatusCode = $get.StatusCode
                FinalUrl = $get.BaseResponse.ResponseUri.AbsoluteUri
            }
        } catch {
            return [pscustomobject]@{
                Url = $Url
                Status = "FAIL"
                StatusCode = ""
                FinalUrl = ""
            }
        }
    }
}

$results = @(
    Test-Url -Url $DemoUrl
    Test-Url -Url $GitHubUrl
)

$results | Format-Table -AutoSize

$failed = $results | Where-Object { $_.Status -ne "OK" }
if ($failed.Count -gt 0) {
    Write-Error "One or more links failed validation."
    exit 1
}

Write-Host "All links validated successfully."
