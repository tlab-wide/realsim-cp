function LidarXYMapAutomationV20(HitPoint,SignalStrength,clock,scenarioName,scenarioID,agentID,sensorID)
    XRange = [-20 60];
    YRange = [-40 40];
    ZRange = [-5 10];

    x = HitPoint(1,:);
    y = HitPoint(2,:);
    z = HitPoint(3,:);
    c = SignalStrength;
    s = 5;
    %new
    points = [x; y; z;]';
    intensity = c(:);
    ptCloud = pointCloud(points, "Intensity", intensity);
    
    filename = sprintf('scenarios/%s/output_data/%s/point_clouds/%s/%s/velodyne_vlp_128/point_cloud_%s.pcd', scenarioName, scenarioID, agentID, sensorID, string(clock));

    if ~exist(sprintf('scenarios/%s/output_data/%s', scenarioName, scenarioID), 'dir')
        mkdir(sprintf('scenarios/%s/output_data/%s', scenarioName, scenarioID));
    end
    if ~exist(sprintf('scenarios/%s/output_data/%s/point_clouds', scenarioName, scenarioID), 'dir')
        mkdir(sprintf('scenarios/%s/output_data/%s/point_clouds', scenarioName, scenarioID));
    end
    if ~exist(sprintf('scenarios/%s/output_data/%s/point_clouds/%s', scenarioName, scenarioID, agentID), 'dir')
        mkdir(sprintf('scenarios/%s/output_data/%s/point_clouds/%s', scenarioName, scenarioID, agentID))
    end
    if ~exist(sprintf('scenarios/%s/output_data/%s/point_clouds/%s/%s', scenarioName, scenarioID, agentID, sensorID), 'dir')
        mkdir(sprintf('scenarios/%s/output_data/%s/point_clouds/%s/%s', scenarioName, scenarioID, agentID, sensorID))
    end
    if ~exist(sprintf('scenarios/%s/output_data/%s/point_clouds/%s/%s/velodyne_vlp_128', scenarioName, scenarioID, agentID, sensorID), 'dir')
        mkdir(sprintf('scenarios/%s/output_data/%s/point_clouds/%s/%s/velodyne_vlp_128', scenarioName, scenarioID, agentID, sensorID))
    end

    pcwrite(ptCloud, filename);

    %new end

  
    
    %figure(1);
    %scatter3(x,y,z,s,c,'filled');
    %xlim(XRange);
    %ylim(YRange);
    %zlim(ZRange);
    %daspect([1 1 1])
    %view(-80,15)

end
